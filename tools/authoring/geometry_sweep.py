#!/usr/bin/env python3
"""Re-audit every prop and say what the last change broke.

    python3 tools/authoring/geometry_sweep.py --save        # take a baseline
    python3 tools/authoring/geometry_sweep.py               # ... change ... diff

Authoring tool. NOT a build, CI or runtime dependency. Needs the dev server up.

WHY. CLAUDE.md's fourth rule is "count the props your change breaks, not the one
it fixes", and until this existed there was nothing that counted. `part_bulge`
names the part on ONE prop and `geometry_audit` scores ONE prop; a change to the
renderer touches all ninety-eight, and the only honest gate on it is all
ninety-eight before and after. It is eight minutes. Three renderer changes in
one session each looked right on the prop that motivated them, and this is what
said which of them to keep.

IT WRITES geometry_audit.json AS IT GOES, which matters because that file is
what `part_bulge --worst` and `depth_scale` read to decide which props are the
bad ones. A sweep that measured everything and left those stale would send the
next investigation at the props that used to be wrong -- the same shape as every
other fault in MISTAKES.md, a measurement that reaches nothing.

READ THE DIFF, NOT THE MEDIAN. A change that moves the median up by flattening
every part is a change that made the props worse, and the median cannot tell you
that; the list of props that moved, and the pictures, can. The measured case:
`alreadyDrawn`'s neighbourhood band scaled to the part's own height scored
0.0003 BETTER on the side median than the local band that replaced it, and it
bought that by telling a jukebox's bubble tubes they were already part of the
cabinet. Two props worse instead of four decided it; the median would have
decided it the other way.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
import geometry_audit as ga                                  # noqa: E402

WORK = ROOT / "tools" / "img2threejs-work"
AXES = ("front", "side", "top")


def sweep(props, extra="", write_json=True):
    """{prop: {axis: iou}} for every prop, and geometry_audit.json refreshed."""
    out = {}
    t0 = time.time()
    for i, d in enumerate(props):
        try:
            report = ga.measure(d, d / "_audit", verbose=False)
        except Exception as e:                                # noqa: BLE001
            print(f"  {d.name}: {e}", flush=True)
            continue
        if write_json:
            (d / "geometry_audit.json").write_text(json.dumps(report, indent=1))
        out[d.name] = {k: v["iou"] for k, v in report.items()
                       if isinstance(v, dict) and "iou" in v}
        for k, v in report.items():
            if isinstance(v, dict) and v.get("daylight", 0) >= 0.004:
                out[d.name][f"_holes_{k}"] = v["daylight"]
        if i % 10 == 9:
            print(f"  .. {i + 1}/{len(props)}  {time.time() - t0:.0f}s",
                  flush=True)
    print(f"\n{len(out)} props in {time.time() - t0:.0f}s")
    return out


def summarise(now):
    for ax in AXES:
        v = sorted(r[ax] for r in now.values() if ax in r)
        if not v:
            continue
        print(f"  {ax:6} n={len(v):3}  median {v[len(v) // 2]:.4f}  "
              f"min {v[0]:.4f}  "
              f"<0.95 {sum(1 for x in v if x < 0.95):3}  "
              f"<0.97 {sum(1 for x in v if x < 0.97):3}")
    ok = sum(1 for r in now.values() if all(r.get(a, 0) >= 0.95 for a in AXES))
    ok7 = sum(1 for r in now.values() if all(r.get(a, 0) >= 0.97 for a in AXES))
    print(f"  all three >= 0.95: {ok}/{len(now)}   >= 0.97: {ok7}/{len(now)}")
    # AND HOLES SEPARATELY, because an IoU barely notices one. See
    # geometry_audit.daylight(): two slits down the whole height of a vending
    # machine moved its side outline by seven points and were the most obvious
    # thing about the prop.
    hol = [(k, a, v) for k, r in now.items() for a, v in r.items()
           if a.startswith("_holes_")]
    if hol:
        print(f"\n  {len(set(k for k, _, _ in hol))} props you can see through:")
        for k, a, v in sorted(hol, key=lambda t: -t[2]):
            print(f"    {k:26} {a[7:]:6} {100*v:5.2f}% of the drawing")


def diff(old, now, bar=0.003):
    rows, tot, n = [], {a: 0.0 for a in AXES}, 0
    for k, r in now.items():
        o = old.get(k)
        if not o or not all(a in r for a in AXES):
            continue
        n += 1
        for a in AXES:
            if a in r and a in o:
                tot[a] += r[a] - o[a]
        rows.append((sum(r.get(a, 0) - o.get(a, 0) for a in AXES), k, o, r))
    rows.sort()
    worse = [r for r in rows if r[0] < -bar]
    better = [r for r in rows if r[0] > bar]
    print(f"\n  {len(worse)} props worse by more than {bar:g}, "
          f"{len(better)} better:")
    for dd, k, o, r in worse + better:
        print(f"    {k:26} {dd:+.4f}  " + "  ".join(
            f"{a} {o.get(a, 0):.3f}->{r.get(a, 0):.3f}" for a in AXES))
    print(f"\n  mean change over {n} props: "
          + "  ".join(f"{a} {tot[a] / max(1, n):+.5f}" for a in AXES))
    return len(worse), len(better)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true",
                    help="record this run as the baseline to diff against")
    ap.add_argument("--baseline", default=str(WORK / "_geometry_baseline.json"))
    ap.add_argument("--only", default=None, help="one prop, for a quick check")
    ap.add_argument("--bar", type=float, default=0.003)
    args = ap.parse_args()

    props = ([Path(args.only).resolve()] if args.only
             else sorted(p.parent for p in WORK.glob("*/layers_front.json")))
    base = Path(args.baseline)
    now = sweep(props)
    summarise(now)
    if args.save:
        base.write_text(json.dumps(now, indent=1))
        print(f"\n  baseline written to {base.relative_to(ROOT)}")
        return 0
    if not base.exists():
        print(f"\n  no baseline at {base}; run with --save first")
        return 0
    diff(json.loads(base.read_text()), now, args.bar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
