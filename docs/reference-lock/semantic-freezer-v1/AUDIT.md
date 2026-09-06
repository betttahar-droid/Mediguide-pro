# Semantic medical freezer v1 audit

Authority inputs: `ref_front_view.png`, `ref_right_side_view.png`, and
`ref_back_view.png` supplied by the user. The right-side orthographic image is
the reliable dimension view; the front and rear images are perspective views.

<SELF_AUDIT>

Proportions calculated:

- Side cabinet is 348 px deep and 819 px high. `348 / 819 = 0.425`.
  Canonical generator depth is `43 / 104 = 0.413`; the 2.8% shallower override
  leaves room for the reference's external rear machinery without making the
  body read too deep.
- Inner front cavity is approximately 278 px wide inside a 351 px front plane.
  `278 / 351 = 0.792`; generator uses `OPEN_HALF = W * 0.795`.
- Orthographic header is 108 px high in an 819 px body. `108 / 819 = 0.132`;
  generator control crown uses `0.971 - 0.837 = 0.134` of H.
- Side vent is 146 px wide across a 348 px side. `146 / 348 = 0.420`;
  generator uses `18.5 / 43 = 0.430`.
- Side vent is 157 px high in an 819 px body. `157 / 819 = 0.192`;
  generator uses `20 / 104 = 0.192`.

Absolute numbers used? NO unintentional absolute scalable body sizes. The
canonical W/H/D envelope scales per axis. Fixed texel pitch, handle dimensions,
decal sizes, and repeated-structure pitch intentionally remain world-unit
constants because those are the invariants being tested.

UVs/Textures/Baked lighting used? NO standard UV unwrap, color texture map, or
baked lighting. The only sampled images are the approved five-tone per-face
semantic masks and transparent fixed-fitting atlas; their quads do not unwrap
or stretch the model.

Structural depth faked with textures? NO. The rear condenser, compressor bay,
feet, door frame, shelves, and handle are geometry. Fine vents, panel seams,
labels, fasteners, and package graphics are surface programs or decals.

Fittings anchored to fixed corners? YES. Fascia controls mount to the named
front plane, rating plate and vent to the service side, warnings and fan grille
to rear planes, and package labels to the frontmost package plane. Runtime
records prove identical fitting and handle world sizes after non-uniform resize.

</SELF_AUDIT>

## Runtime acceptance

- Status: PASS
- Normal model: 2,484 triangles, 99 parts, 24 fixed decals, 4 shelves.
- Resized model (1.45 x 1.20 x 1.30): 2,556 triangles, 105 parts, 24 fixed
  decals, 5 shelves.
- Palette counts: front 34, isometric 48, side 25, rear 29, resized 47.
- Fixed handle dimensions: unchanged.
- Fixed fitting dimensions: unchanged.
- Structural response: shelf count grows from four to five at fixed pitch.
- Shader/page errors: none.

## Generation review

Nano Banana 2 produced all requested semantic roles but did not obey the exact
grid. The compiler therefore accepts eight named face regions and eight named
fittings only. Three duplicate/unrequested regions are recorded as rejected in
`public/textures/semantic-freezer-v1.json`.

The audit also exposed and corrected a shared shader defect: face roles were
previously classified with camera-space normals, so textures could change role
when the camera moved. They now use model/world-aligned normals and remain stable
from front, side, rear, and isometric views.
