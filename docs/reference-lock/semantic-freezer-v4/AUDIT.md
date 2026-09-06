# Semantic freezer v4 — evidence audit

Status: **PASS**. Geometry is unchanged. V4 replaces coarse source labels with
per-region provenance and compiles only reviewed direct or reconstructed evidence.

## Diagnostic contract

- Five passes per view: raw, part-ID, world face-normal, linear depth, anchor-ID.
- Three locked views: front isometric, orthographic side, rear isometric.
- Nano is asked for one view paintover, never an atlas.

## Compiled evidence

- Direct information regions: **25**.
- Rectified pixel regions: **25**. Their meaning comes from direct
  authority, while geometry-aligned paintovers remove baked camera perspective.
- Unsupported reconstructed regions: **0**.
- Invented regions: **0**.
- Every fixed fitting has a semantic anchor; every repeated field is a fixed-world microfield.

## Nano candidate gates

- iso: **MISSING**
- side: **MISSING**
- back: **MISSING**

Missing or rejected Nano candidates do not block this build because they are not
used as evidence. Any later reconstructed region must pass the gate before compilation.

## Compiler checks

- uniqueRegionIds: **PASS**
- allRuntimeRegionsApproved: **PASS**
- allApprovedRegionsHaveEvidence: **PASS**
- noInventedRegionCompiled: **PASS**
- allFixedRegionsAnchored: **PASS**
- noUnresolvedConflicts: **PASS**
- allRectifiedPixelSourcesPassInternalGate: **PASS**
- diagnosticContractComplete: **PASS**
