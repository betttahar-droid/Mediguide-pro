# Semantic freezer V7 adaptive-texture audit

Status: **PASS**

- compilerContractPasses: **PASS**
- allCorrespondencesConsumed: **PASS**
- runtimeUnitBoundarySane: **PASS**
- baseCondenserMeasuredExtent: **PASS**
- widthExpansionChangesOnlyExtent: **PASS**
- heightExpansionChangesOnlyExtent: **PASS**
- condenserPitchNeverScales: **PASS**
- condenserLineWidthNeverScales: **PASS**
- condenserCountsGrow: **PASS**
- condenserMarginsStayFixed: **PASS**
- condenserUsesSemanticProceduralField: **PASS**
- sideVentBackAnchorFixed: **PASS**
- sideVentMovesWithRearEdge: **PASS**
- sideRatingFrontAnchorFixed: **PASS**
- rearWarningTracksPanelTopAndCenter: **PASS**
- rearDoNotTracksPanelBottom: **PASS**
- fixedDecalsRemainFixed: **PASS**
- handleAndFixedGeometryRemainFixed: **PASS**
- rearLabelsLayerAboveField: **PASS**
- ventOwnsOverlapInsteadOfWear: **PASS**
- faceOrientationContractComplete: **PASS**
- noDirectionFlippingOrCheckerMirroring: **PASS**
- fixedCameraPixelPitchStable: **PASS**
- shaderPitchMatchesContract: **PASS**
- noMagentaKeyLeak: **PASS**
- runtimeClean: **PASS**

## Evidence

```json
{
  "ventBackOffsets": [
    12.513,
    12.512999999999998
  ],
  "condenserSizes": {
    "base": [
      38.828,
      71.154
    ],
    "width": [
      58.628,
      71.154
    ],
    "height": [
      38.828,
      101.4492
    ]
  },
  "repeatCounts": {
    "base": [
      15,
      8
    ],
    "width": [
      23,
      8
    ],
    "height": [
      15,
      12
    ]
  },
  "pixelPitch": {
    "base": {
      "row": 186,
      "runs": 17,
      "medianPitchPixels": 15.0
    },
    "width": {
      "row": 186,
      "runs": 25,
      "medianPitchPixels": 15.0
    }
  },
  "magentaPixels": 0
}
```
