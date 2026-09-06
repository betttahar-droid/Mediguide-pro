# Prop Factory runtime evidence contract

The screenshot runner writes `audit.json` with this shape:

```json
{
  "records": [
    {
      "scale": [1, 1, 1],
      "errors": [],
      "faceBasis": {},
      "textureLayers": [],
      "correspondenceIds": [],
      "fixedFittingSizes": [],
      "rigidPartSizes": [],
      "fittingPlacements": [
        {
          "id": "sideVentPanel",
          "face": "left",
          "layer": "structural-graphic",
          "centerTexels": [8.987, 16.095],
          "sizeTexels": [21.431, 24.512],
          "planeTexels": -22.5
        }
      ],
      "adaptiveTexturePanels": [
        {
          "id": "condenserField",
          "layer": "structural-graphic",
          "boundsTexels": [-18.776, 25.754, 20.052, 96.908],
          "sizeTexels": [38.828, 71.154],
          "pitchTexels": [2.45, 8.2],
          "lineWidthTexels": [0.52, 0.72],
          "repeatCounts": [15, 8],
          "marginsTexels": [3.224, 1.948, 25.754, 4.076]
        }
      ]
    }
  ]
}
```

Values are model texels, not Three.js world coordinates or screen pixels. The screenshot path stored on each record lets Prop Factory independently verify visible pixel frequency.
