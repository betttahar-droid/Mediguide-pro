#!/usr/bin/env python3
"""Render a prop at 1x and 1.5x tall and score the banding, for one prop or all.

    python3 tools/authoring/tall_probe.py tools/img2threejs-work/v36_arcade_cabinet
    python3 tools/authoring/tall_probe.py --all --out tall_before.json

Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server up.

WHY. ROADMAP section 0 names 24 props that still band at 1.5x tall, with a rise
per prop -- and nothing in the repo reproduces those numbers from a clean
checkout. `repeat_score` reads a round folder the judge loop made; the corpus
branch carries no round folders, so the one measurement the tall axis is steered
by cannot be taken. This makes the two renders `repeat_score` wants and hands
them to it, so the before/after of a growth-place change is a number rather than
a picture.

IT IS THE RISE THAT COUNTS, never the bare score -- the reason is in
`repeat_score`'s own docstring: a vending machine has shelves before anyone
resizes it. Same convention here: base is w=1,h=1 and the comparison is against
the prop's own drawn self.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
import geometry_audit as ga                                   # noqa: E402
import repeat_score as rs                                     # noqa: E402

WORK = ROOT / "tools" / "img2threejs-work"


def probe(d, tall=1.5, out_name="_tall"):
    """-> repeat_score.judge() for this prop, or None if nothing rendered."""
    d = Path(d).resolve()
    out = d / out_name
    qs = [f"dir=/{d.relative_to(ROOT).as_posix()}&w=1&h=1&x=1",
          f"dir=/{d.relative_to(ROOT).as_posix()}&w=1&h={tall}&x=1"]
    ga.shoot(out, qs)
    return rs.judge(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prop_dir", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--tall", type=float, default=1.5)
    ap.add_argument("--out", help="write {prop: rise} json here")
    args = ap.parse_args()

    props = ([p for p in sorted(WORK.iterdir())
              if p.is_dir() and (p / "layers_front.json").exists()]
             if args.all else [Path(args.prop_dir)])

    table = {}
    for p in props:
        r = probe(p, args.tall)
        if not r:
            print(f"  {p.name:26} no render")
            continue
        base = r["base"]["peak"]
        for row in r["sizes"]:
            rise = row["peak"] - base
            table[p.name] = {"base": base, "peak": row["peak"],
                             "rise": round(rise, 3), "lag": row["lag"],
                             "flat_rise": round(row["flat"] - r["base"]["flat"], 3),
                             "faults": len(r["faults"])}
            print(f"  {p.name:26} base {base:.3f}  {row['size']:>9} "
                  f"{row['peak']:.3f}  rise {rise:+.3f}  "
                  f"flat {row['flat'] - r['base']['flat']:+.3f}"
                  f"{'  BANDING' if rise >= 0.22 else ''}")
    if args.out:
        Path(args.out).write_text(json.dumps(table, indent=1))
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
