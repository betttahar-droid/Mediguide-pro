#!/usr/bin/env python3
"""Which judge to ask, measured against a fault arithmetic can see.

    python3 tools/authoring/judge_bench.py --each 4

Authoring tool. NOT a build, CI or runtime dependency.

WHY. `gemini_judge`'s model list was ordered by price among models that answer
in the schema at all, and that is a weak claim: two candidates differed by a
factor of three in faults reported on the same prop, and nothing said whether
that was thoroughness or noise. Ordering graders by what they cost is how you
end up with the situation this repo already measured -- two judges scoring a
cabinet carrying FIVE STACKED MARQUEES level with the corrected cabinet beside
it.

WHAT MAKES THIS POSSIBLE is that one fault class is measurable without asking
anyone. `repeat_score` autocorrelates the row-luminance profile of the renders
the loop already made, against the prop's own 1x render, and separates every
case previously judged by eye. It is the ground truth here, and it is the RIGHT
fault class to test on: 181 of 306 blocking faults across three runs were one
sentence in different words -- a repeat, seam, smear or band a player could
point at -- and CLAUDE.md's finding is that the language judges report that
class constantly and cannot actually see it.

So: take the props whose renders arithmetic says carry a repeat, and the props
it says are clean, ask each judge the real JUDGE prompt, and score whether the
judge NAMES a repeat on the props that have one and stays quiet on the props
that do not. A judge that cries repeat on everything scores as badly as one that
never does, which is the point -- precision and recall, not fault count.

HONEST LIMIT, and it is a real one. This measures one fault class, on a handful
of props, and a judge good at spotting duplication is not thereby good at
spotting a door hinged the wrong way. It settles the question it is pointed at
and no more. What it is NOT is a proxy invented to rank models: it is the
pipeline's own arithmetic, already wired in front of the judges, asked whether
the judges agree with it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
import repeat_score as rs                                    # noqa: E402
import gemini_judge as gj                                    # noqa: E402

WORK = ROOT / "tools" / "img2threejs-work"

# The vocabulary the judges actually use for this fault, taken from the verdict
# logs rather than guessed: "duplicated sign", "tiling repeat", "the texture is
# stretched and banded", "reads as a bug".
SAYS_REPEAT = re.compile(
    r"repeat|repea|duplicat|tiled|tiling|stack(ed|ing)?|smear|band(ed|ing)\b"
    r"|multiple cop|twice|three times|cloned|mirror(ed)?\b", re.I)


def ground_truth(each):
    """(dirty, clean) — props whose renders arithmetic calls repeated, and not.

    Taken from opposite ends of the measured range, not from a threshold: the
    question is whether a judge can tell the extremes apart, and if it cannot
    there is no point asking about the middle.
    """
    rows = []
    for d in sorted(p for p in WORK.glob("*/") if p.is_dir()):
        # A prop that cannot be ASKED about is not evidence either way. Three
        # arcade cabinets have renders but no scale_rules.json or front.png, and
        # counting them as judge failures put two of the four "clean" props out
        # of the sample and flattered whichever model happened to get the rest.
        if not all((d / f).exists() for f in
                   ("front.png", "scale_rules.json", "parts_front.json")):
            continue
        rounds = sorted([p for p in d.glob("r[0-9]*") if p.is_dir()],
                        key=lambda p: int(p.name[1:] or 0), reverse=True)
        for r in rounds[:1]:
            try:
                v = rs.judge(r)
            except Exception:
                v = None
            if not v or not v.get("sizes"):
                continue
            if not rs.shots(r)[0]:          # no 1x render to compare against
                continue
            base = v["base"]["peak"]
            worst = max(s["peak"] - base for s in v["sizes"])
            rows.append((worst, d, r))
    rows.sort(reverse=True)
    return rows[:each], rows[-each:]


def ask(model, d, r, timeout=300):
    """The real JUDGE prompt, the real renders, one model."""
    from make_prop import JUDGE
    sr = json.loads((d / "scale_rules.json").read_text())
    parts = json.loads((d / "parts_front.json").read_text())["parts"]
    # shots() returns (base, [(label, path), ...]) -- the 1x render and the
    # enlarged ones. The judge prompt wants them in that order: reference,
    # original, wider, taller.
    base, bigs = rs.shots(r)
    imgs = [str(d / "front.png")] + ([str(base)] if base else []) \
        + [str(p) for _lab, p in bigs[:2]]
    prompt = JUDGE.format(
        asset=d.name.split("_", 1)[-1].replace("_", " "),
        parts="\n".join(f"- {p['name']}" for p in parts[:40]),
        wider=sr.get("wider_means", ""), taller=sr.get("taller_means", ""),
        wx=sr.get("max_wider", 2), hx=sr.get("max_taller", 1.5))
    got, used = gj._via_openrouter(prompt, imgs, timeout, models=(model,))
    faults = got.get("faults") or []
    said = any(SAYS_REPEAT.search(str(f.get("fault", ""))) for f in faults)
    return said, len(faults), got.get("looks_good")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--each", type=int, default=4,
                    help="props from each end of the arithmetic's range")
    ap.add_argument("--models", default=",".join(gj.OR_MODELS))
    args = ap.parse_args()

    dirty, clean = ground_truth(args.each)
    print(f"arithmetic says REPEATED: "
          + ", ".join(f"{d.name}({w:+.2f})" for w, d, _ in dirty))
    print(f"arithmetic says CLEAN:    "
          + ", ".join(f"{d.name}({w:+.2f})" for w, d, _ in clean) + "\n")

    for model in [m.strip() for m in args.models.split(",") if m.strip()]:
        hit = miss = false = quiet = 0
        for w, d, r in dirty:
            try:
                said, n, lg = ask(model, d, r)
            except Exception as e:
                print(f"  {model:32} {d.name:24} FAILED {str(e)[:50]}"); continue
            hit, miss = hit + said, miss + (not said)
            print(f"  {model:32} {d.name:24} repeat={w:+.2f}  "
                  f"judge {'FOUND it' if said else 'MISSED it'}  ({n} faults)")
        for w, d, r in clean:
            try:
                said, n, lg = ask(model, d, r)
            except Exception as e:
                print(f"  {model:32} {d.name:24} FAILED {str(e)[:50]}"); continue
            false, quiet = false + said, quiet + (not said)
            print(f"  {model:32} {d.name:24} clean ={w:+.2f}  "
                  f"judge {'cried repeat' if said else 'agreed'}    ({n} faults)")
        tot = hit + miss + false + quiet
        print(f"  -> {model}: found {hit}/{hit+miss} real, "
              f"false alarm on {false}/{false+quiet} clean, "
              f"{(hit+quiet)}/{tot} correct\n")


if __name__ == "__main__":
    main()
