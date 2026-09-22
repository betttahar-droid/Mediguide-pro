#!/usr/bin/env python3
"""Every drawing bought, what it cost, and whether it was used.

    python3 tools/authoring/image_ledger.py              # the table
    python3 tools/authoring/image_ledger.py --by aspect  # ... split by canvas
    python3 tools/authoring/image_ledger.py --tail 20    # the last N purchases

Authoring tool. NOT a build, CI or runtime dependency. Writes one JSONL under
`tools/img2threejs-work/`, which is gitignored -- a spend record is local
billing data and does not belong in a public repo.

WHY. "Is there a cheaper way to buy a sheet?" was asked and could only be
answered by argument, because nothing wrote the answer down. `concept_sheet`
counts spend in a module-level dict that dies with the process; it prints the
per-call price to a terminal nobody keeps; and the thing that actually decides
cost -- whether the drawing SURVIVED the check that follows it -- is known in a
different file and never joined to the price at all.

THAT GAP COST 24% OF A RUN AND HID IT. `image_bench` scored gpt-5-image-mini
8 of 8 and it went to the head of the ladder. On the next six live `wide_art`
purchases it was refused six times out of six, every one of them for returning
a 1.00 square against a canvas of 7.53:1 or 21.10:1, and every one of them
billed $0.0434-$0.0449. $0.177 of a $0.74 run, for nothing, and the only reason
it was ever found is that a human asked a question and someone read scrollback.
A ledger answers it in a second and would have answered it the first time.

WHAT IT RECORDS, and why each field is here rather than derived later:

  the CANVAS ASPECT, because that is the variable the bench got wrong. Every
    ask this pipeline makes is a non-square canvas with magenta to fill -- the
    canvas IS the request -- and a model that returns a square is useless here
    at any price. A table of dollars per token cannot show that; a table split
    by canvas aspect shows it on the first row.
  the RETURNED ASPECT beside it, so a refusal for the wrong shape is legible
    without reading the caller's `why`.
  the CALLER, taken off the stack rather than passed, because nine tools call
    `generate_image` and a ledger that needed all nine edited would have been
    wired into two of them.
  the VERDICT as a SEPARATE ROW. A purchase is known at the moment of purchase
    and its fate is known in another file some seconds later, and the honest
    shape for that is an append, not a field that would have to be guessed at
    write time. A buy with no verdict row reads as `?` and is counted as such,
    never quietly as accepted -- which is the same rule as everywhere else
    here: a measurement that can return nothing must not have nothing win.

WHAT IT DELIBERATELY DOES NOT DO. It does not cap spend, and it does not pick
the model. `concept_sheet` already refuses below `PROP_IMAGE_BUDGET` and
already orders `OR_LADDER`; a second opinion on either, living in a file
nothing imports at decision time, is a signal that reaches nothing. This is
the evidence those two are set from, and the next time the order is argued
about it should be argued from `--by model` on a real run.
"""
import argparse
import inspect
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = Path(os.environ.get(
    "PROP_IMAGE_LEDGER", ROOT / "tools" / "img2threejs-work" / "_image_spend.jsonl"))

# The tools that buy drawings, so a purchase can be attributed without every
# one of them being edited. Anything else on the stack is a helper.
_MINE = {"image_ledger", "concept_sheet"}


def _caller():
    """The authoring tool that asked for this drawing, off the stack."""
    try:
        for f in inspect.stack()[1:]:
            stem = Path(f.filename).stem
            if stem not in _MINE and "/tools/authoring/" in f.filename.replace(
                    os.sep, "/"):
                return stem
    except Exception:                                         # noqa: BLE001
        pass
    return "?"


def png_size(path):
    """(w, h) for a PNG, off the IHDR. None for anything else.

    Straight off the header rather than through PIL: this is called on the way
    past a purchase, in the one module that talks to the image API, and that
    module has no imaging dependency today. Adding one so a log line can say
    `620x250` would be the tail wagging the dog.
    """
    try:
        b = Path(path).read_bytes()[:26]
        if b[:8] != b"\x89PNG\r\n\x1a\n" or b[12:16] != b"IHDR":
            return None
        return struct.unpack(">II", b[16:24])
    except Exception:                                         # noqa: BLE001
        return None


def _append(row):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:                                         # noqa: BLE001
        pass          # a ledger must never be able to fail a build


def buy(model, usd, path, canvas=None, got=None, note=""):
    """Record one paid call. `canvas` is what was asked for, `got` what arrived.

    Both as (w, h) or None. Never raises: a drawing that was bought and could
    not be logged is still a drawing, and a tool that died writing its own
    receipt would be the most expensive bug in the file.
    """
    row = {"t": round(time.time()), "ev": "buy", "model": model,
           "usd": round(float(usd or 0.0), 6), "by": _caller(),
           "path": str(path)}
    if canvas:
        row["canvas"] = [int(canvas[0]), int(canvas[1])]
        row["ask_ar"] = round(canvas[0] / max(1.0, float(canvas[1])), 3)
    if got:
        row["got"] = [int(got[0]), int(got[1])]
        row["got_ar"] = round(got[0] / max(1.0, float(got[1])), 3)
    if note:
        row["note"] = str(note)[:200]
    _append(row)
    return row


def verdict(path, ok, why=""):
    """Record whether the drawing at `path` survived the check that follows it.

    The caller's own acceptance test, not a second one -- `wide_art.check`,
    `tall_body.check`, the aspect bar. Whatever decides that the artwork is
    composited decides this.
    """
    _append({"t": round(time.time()), "ev": "verdict", "path": str(path),
             "ok": bool(ok), "why": str(why)[:160]})


def rows(log=None):
    p = Path(log or LOG)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:                                     # noqa: BLE001
            continue
    return out


def join(rs):
    """[buy] with `ok` and `why` filled in from the verdict that followed it.

    A verdict is matched to the most recent UNRESOLVED buy on the same path,
    because a re-ask writes the same file again: `wide_art` gives every attempt
    the same `dst` and only renames it once all three are refused. Matching on
    path alone would give the first attempt the third attempt's verdict.
    """
    buys, open_ = [], {}
    for r in rs:
        if r.get("ev") == "buy":
            buys.append(dict(r, ok=None, why=""))
            open_.setdefault(r["path"], []).append(len(buys) - 1)
        elif r.get("ev") == "verdict":
            q = open_.get(r["path"])
            if q:
                b = buys[q.pop(0)]
                b["ok"], b["why"] = r.get("ok"), r.get("why", "")
    return buys


def _bucket(b, by):
    if by == "model":
        return b.get("model", "?")
    if by == "caller":
        return b.get("by", "?")
    if by == "aspect":
        a = b.get("ask_ar")
        if a is None:
            return "unknown"
        # THE BUCKETS ARE THE PIPELINE'S OWN SHAPES, not even decades. A sheet
        # is drawn near 1:1, a widened part near 2-4:1, and a strip of moulding
        # runs past 20:1 -- and the fault this file was written for showed up
        # only past about 2:1, so that is where the first edge goes.
        return ("square (<1.3)" if a < 1.3 else "wide (1.3-3)" if a < 3
                else "very wide (3-8)" if a < 8 else "strip (>8)")
    return f"{b.get('model','?')}  {b.get('by','?')}"


def report(buys, by="model"):
    if not buys:
        print(f"  no purchases recorded in {LOG}")
        print("  (nothing has been bought since the ledger was wired in)")
        return
    g = {}
    for b in buys:
        g.setdefault(_bucket(b, by), []).append(b)
    print(f"  {len(buys)} drawing(s), ${sum(b['usd'] for b in buys):.4f} total\n")
    print(f"  {by:34} {'calls':>5} {'ok':>4} {'no':>4} {'?':>3} "
          f"{'spent':>9} {'$/accepted':>11}")
    print("  " + "-" * 76)
    for k, v in sorted(g.items(), key=lambda kv: -sum(b["usd"] for b in kv[1])):
        ok = sum(1 for b in v if b["ok"] is True)
        no = sum(1 for b in v if b["ok"] is False)
        un = sum(1 for b in v if b["ok"] is None)
        spent = sum(b["usd"] for b in v)
        # A MODEL WITH NOTHING ACCEPTED HAS NO PRICE, and printing its per-call
        # rate there would be the exact mistake this file exists to record:
        # gpt-5-image-mini's $0.044 a call is not $0.044 a drawing when no
        # drawing arrived. An infinity is the honest cell -- but only when the
        # refusals are KNOWN. A row that is all unresolved has not been graded
        # at all, and `inf` would read as a verdict it has not earned.
        per = (f"{spent / ok:9.4f}" if ok
               else "unresolved" if not no
               else "       inf" if spent else "    -")
        print(f"  {k[:34]:34} {len(v):5} {ok:4} {no:4} {un:3} "
              f"{spent:9.4f} {per:>11}")
    bad = [b for b in buys if b["ok"] is False]
    if bad:
        waste = sum(b["usd"] for b in bad)
        print(f"\n  ${waste:.4f} of that bought nothing "
              f"({100 * waste / max(1e-9, sum(b['usd'] for b in buys)):.0f}% "
              f"of the bill, {len(bad)} refused drawings)")
        # AND WHETHER THE REFUSALS SHARE A SHAPE, which is the one thing a
        # price table cannot say. Six refusals for six different reasons is a
        # hard subject; six for one reason is a model that cannot do the job.
        why = {}
        for b in bad:
            why[(b.get("why") or "?")[:52]] = why.get(
                (b.get("why") or "?")[:52], 0) + 1
        for w, n in sorted(why.items(), key=lambda kv: -kv[1])[:6]:
            print(f"    {n:3}x  {w}")
    un = [b for b in buys if b["ok"] is None]
    if un:
        print(f"\n  {len(un)} purchase(s) have no verdict recorded; their "
              f"caller does not report one yet, so they are counted as "
              f"neither. Do not read them as accepted.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--by", default="model",
                    choices=["model", "caller", "aspect", "both"])
    ap.add_argument("--tail", type=int, default=0)
    ap.add_argument("--log", default=None)
    args = ap.parse_args()

    buys = join(rows(args.log))
    report(buys, args.by)
    if args.tail:
        print(f"\n  last {min(args.tail, len(buys))} purchases:")
        for b in buys[-args.tail:]:
            mark = {True: "ok ", False: "NO ", None: " ? "}[b["ok"]]
            # `asked -> arrived`, and nothing after the arrow when nothing
            # arrived: a billed call that returned no picture is a different
            # animal from one that returned the wrong shape, and printing
            # `->0.00` for it would read as the second.
            ar = (f"{b['ask_ar']:.2f}" if b.get("ask_ar") else "")
            if ar and b.get("got_ar"):
                ar += f"->{b['got_ar']:.2f}"
            print(f"    {mark} ${b['usd']:.4f}  {b['model'].split('/')[-1]:28} "
                  f"{b.get('by', '?'):14} {ar:>14}  "
                  f"{Path(b['path']).name[:30]}")
            if b["ok"] is False and b.get("why"):
                print(f"           {b['why'][:88]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
