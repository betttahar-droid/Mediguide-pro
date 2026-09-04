#!/usr/bin/env python3
"""Generate the orthographic turnaround that voxel_carve.py carves from.

    python3 tools/voxel-fridge/nano_views.py
    python3 tools/voxel-fridge/nano_views.py side top     # regenerate some

Authoring tool. NOT a build, CI or runtime dependency.

THE POINT OF THE TURNAROUND. voxel_carve.py intersects three orthographic
silhouettes to get a volume, so the model it produces is only as good as the
views agree with each other. That makes multi-view CONSISTENCY the whole job
of this step — which is what Nano Banana 2 is actually built for, and why it
belongs here rather than being asked to produce 3D directly.

Consistency is bought two ways:
  - each view after the first is generated WITH the previous ones attached as
    reference images, so the model matches proportions rather than reinventing
    them;
  - every prompt demands strict orthographic projection, a flat background and
    no shadow, because a cast shadow or a hint of perspective is silhouette the
    carver will happily treat as solid.

WHAT THE CARVER NEEDS, and what a pretty picture would get wrong:
  flat single-colour background   the silhouette is found by difference from
                                  the corner colour
  no drop shadow                  a shadow is object as far as a silhouette is
                                  concerned
  no perspective, no foreshortening   the carve assumes an orthographic camera
  object fills the frame          the grid is derived from the object's aspect
  the SAME object in every view   or the intersection is nonsense
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "authoring"))
from concept_sheet import generate_image, load_key  # noqa: E402

SUBJECT = (
    "a retro pharmacy vaccine fridge: a tall narrow cabinet about three times "
    "taller than it is wide, standing on four dark purple corner feet, with a "
    "deep teal-green base block carrying a tan louvred condenser grille, a "
    "cream painted body with pale blue-grey side panels, a full-height glass "
    "door showing four pale mint shelves against a dark teal interior, a slim "
    "purple vertical handle, and a cream crown cap with a small dark "
    "temperature display reading 4C"
)

STYLE = (
    "16-bit pixel art, hard-edged chunky pixels, a strictly limited palette of "
    "about sixteen colours, flat shading with NO gradients and NO soft edges. "
    "STRICT ORTHOGRAPHIC PROJECTION: no perspective, no foreshortening, no "
    "vanishing point. Absolutely flat single-colour background, NO drop shadow, "
    "NO ground plane, NO reflection. The object fills the frame with a small "
    "even margin. No text, no labels, no annotations, no watermark."
)

VIEWS = {
    "front": "Draw the FRONT elevation, looking straight at the door, dead on.",
    "side": ("Draw the LEFT SIDE elevation of the SAME cabinet, looking straight "
             "at its flank, dead on. It must be exactly the same height as the "
             "attached front view, and show the plain side panel with its "
             "horizontal joint, not the door."),
    "top": ("Draw the TOP view of the SAME cabinet, looking straight down from "
            "above. Its width must exactly match the attached front view and "
            "its depth must exactly match the attached side view. Show the "
            "cream crown cap from above."),
}
ORDER = ["front", "side", "top"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="views to generate; default all")
    ap.add_argument("--out", default=str(HERE / "views"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    key = load_key()
    wanted = args.names or ORDER

    failed = []
    for name in ORDER:
        if name not in wanted:
            continue
        # Attach every view already made, so each one is generated against the
        # others rather than from the description alone. This is the single
        # thing that makes the three silhouettes agree well enough to intersect.
        refs = [out / f"{n}.png" for n in ORDER[:ORDER.index(name)]
                if (out / f"{n}.png").exists()]
        prompt = f"{STYLE}\n\nSubject: {SUBJECT}\n\n{VIEWS[name]}"
        print(f"generating {name} (refs: {[r.stem for r in refs] or 'none'}) ...", flush=True)
        try:
            generate_image(prompt, out / f"{name}.png", key, refs=refs)
        except Exception as exc:
            failed.append(name)
            print(f"  FAILED {name}: {str(exc)[:140]}")
    if failed:
        print(f"  retry with: nano_views.py {' '.join(failed)}")
    else:
        print(f"\nwrote {out}/  — now carve them:\n"
              f"  python3 tools/voxel-fridge/voxel_carve.py \\\n"
              f"      --front {out}/front.png --side {out}/side.png "
              f"--top {out}/top.png --height 96 --out {HERE}/carved.json")


if __name__ == "__main__":
    main()
