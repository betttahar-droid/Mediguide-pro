param(
  [ValidateSet('All', 'Geometry', 'Textures', 'Parts', 'Atlas')]
  [string]$Pass = 'All',
  [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$lock = Join-Path $root 'docs\reference-lock\vaccine-fridge-v2'
$authorityPath = Join-Path $root 'docs\concept\vaccine-fridge-turnaround-v1.png'
$envPath = Join-Path $root '.env'

$keyLine = Get-Content -LiteralPath $envPath |
  Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()

New-Item -ItemType Directory -Force -Path $lock | Out-Null
$model = 'gemini-3.1-flash-image'
$uri = "https://generativelanguage.googleapis.com/v1/models/$model`:generateContent"

function Invoke-SourcePass {
  param(
    [string]$Name,
    [string]$Prompt,
    [string]$AspectRatio,
    [string[]]$ReferencePaths = @($authorityPath)
  )

  $textPath = Join-Path $lock "$Name-response.txt"
  $promptPath = Join-Path $lock "$Name-prompt.txt"
  [IO.File]::WriteAllText($promptPath, $Prompt)
  if ($PrepareOnly) {
    Write-Output "PREPARED=$promptPath"
    return
  }

  $requestParts = @()
  foreach ($referencePath in $ReferencePaths) {
    if (-not (Test-Path -LiteralPath $referencePath)) {
      throw "Missing reference image for $Name`: $referencePath"
    }
    $referenceBytes = [IO.File]::ReadAllBytes($referencePath)
    $requestParts += @{ inline_data = @{
      mime_type = 'image/png'
      data = [Convert]::ToBase64String($referenceBytes)
    } }
  }
  $requestParts += @{ text = $Prompt }
  $aspectRatioEnum = @{
    '1:1' = 'ASPECT_RATIO_ONE_BY_ONE'
    '16:9' = 'ASPECT_RATIO_SIXTEEN_BY_NINE'
  }[$AspectRatio]
  if (-not $aspectRatioEnum) { throw "Unsupported aspect ratio: $AspectRatio" }
  $body = @{
    contents = @(@{
      parts = $requestParts
    })
    generationConfig = @{
      responseModalities = @('TEXT', 'IMAGE')
      # The raw REST v1 endpoint expects protobuf enum names here. SDKs accept
      # friendly values such as 16:9 and 2K, but forwarding those strings in a
      # hand-authored REST payload returns INVALID_ARGUMENT.
      responseFormat = @{ image = @{
        aspectRatio = $aspectRatioEnum
        imageSize = 'IMAGE_SIZE_TWO_K'
      } }
    }
  } | ConvertTo-Json -Depth 12 -Compress

  try {
    $response = Invoke-RestMethod -Method Post -Uri $uri -Headers @{
      'x-goog-api-key' = $apiKey
    } -ContentType 'application/json' -Body $body -TimeoutSec 300
  }
  catch {
    $detail = $_.ErrorDetails.Message
    if (-not $detail -and $_.Exception.Response) {
      $reader = [IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
      try { $detail = $reader.ReadToEnd() } finally { $reader.Dispose() }
    }
    if ($detail) { throw "Gemini request failed for $Name`: $detail" }
    throw
  }

  $imageData = $null
  $imageMimeType = $null
  $responseText = [System.Collections.Generic.List[string]]::new()
  foreach ($candidate in $response.candidates) {
    foreach ($part in $candidate.content.parts) {
      if ($part.text) { $responseText.Add($part.text) }
      if ($part.inlineData) {
        $imageData = $part.inlineData.data
        $imageMimeType = $part.inlineData.mimeType
      }
      if ($part.inline_data) {
        $imageData = $part.inline_data.data
        $imageMimeType = $part.inline_data.mime_type
      }
    }
  }
  if (-not $imageData) {
    $finish = ($response.candidates | ForEach-Object { $_.finishReason }) -join ','
    throw "Gemini returned no image for $Name (finish=$finish)"
  }

  $extension = switch -Regex ($imageMimeType) {
    'jpe?g' { '.jpg'; break }
    'webp' { '.webp'; break }
    default { '.png' }
  }
  $imagePath = Join-Path $lock "$Name$extension"
  [IO.File]::WriteAllBytes($imagePath, [Convert]::FromBase64String($imageData))
  [IO.File]::WriteAllText($textPath, ($responseText -join [Environment]::NewLine))
  Write-Output "SAVED=$imagePath"
}

$geometryPrompt = @'
The supplied image vaccine-fridge-turnaround-v1 is the ONLY design authority. Do not redesign, beautify, simplify, add, remove, or relocate anything. Produce a production GEOMETRY CORRECTION SHEET for reconstructing this exact object as a low-poly Blender mesh on a 32-pixel grid.

First internally trace the FRONT view silhouette and feature boundaries, then the SIDE view depth boundaries, then use the ISO view only to resolve depth ordering and bevel direction. The source is an AI turnaround, so when opposing views conflict: FRONT controls width and height, SIDE controls depth, ISO controls layering. Never average away a visible step.

Show large orthographic FRONT, RIGHT, BACK, TOP, and a cutaway ISOMETRIC of one identical fridge. Use a plain grid. Preserve the exact tall narrow silhouette, three-stage stepped crown, projecting crown fascia, thin dark separator under the crown, cream carcass corner posts, recessed cream front frame, inset teal door leaf, real glass plane, deep empty cavity, four shelf trays with front lips, left purple handle with two attachment blocks, lower teal condenser box, inset ochre grille, stepped lower transition, plum plinth rail, and four feet. No products.

Use the following already measured source coordinates as hard constraints, in model pixels, where 32 px = 1 Blender unit: overall height 96; front overall width 38.75; side overall depth 36.75; feet 0..1.125; plinth 1.125..3.25; condenser 3.25..19; carcass 19..87; crown fascia 87..94; crown roof 94..96; door outer x -15..15 z 22..82; glass x -12..12 z 27..79; handle x -18..-15 z 43..62; grille x -13..13 z 5..16; display x -5..6 z 88..93; shelf elevations 36,48,60,72.

Add enlarged numbered construction sections for: A crown profile, B front outer-frame and inset door depth stack, C glass/cavity/shelf depth stack, D condenser-to-carcass transition, E plinth/foot profile, F handle mounts. Mark which visible marks are GEOMETRY and which are TEXTURE ONLY. Rust, chips, scratches, flush bolt pixels, baked highlights, and panel color seams are texture only. Bevels, ledges, overhangs, frame steps, door thickness, handle mounts, shelf lips, and silhouette-changing feet are geometry.

The result must be a technical sheet, neutral clay geometry with dark outlines, no decorative textures, no lighting gradients, no perspective in orthographic panels, and no alternate design.
'@

$texturePrompt = @'
The supplied image vaccine-fridge-turnaround-v1 is the ONLY design and color authority. Do not redesign it and do not borrow generic fridge details. Produce a production SEMANTIC PIXEL-TEXTURE DECOMPOSITION for this exact fridge. This is a flat texture-authoring sheet, not a beauty render.

Reconstruct the visible texture character exactly: warm ivory enamel, blue-gray steel side panels, deep desaturated teal door/cavity/condenser, dark green glass, pale shelf steel, aubergine-purple handle and plinth, ochre-gold grille, dark plum seams, mint display digits reading 4C, and the small orange display indicator. Use hard square low-resolution pixels, nearest-neighbour edges, restrained baked value bands, no antialiasing, no photographic noise, and no smooth gradients.

Lay out separate large, flat, front-facing islands for:
1 cream frame vertical edge, horizontal edge, protected outer corner, and quiet tileable centre;
2 steel side-panel protected top corner, protected bottom corner, vertical edge strip, horizontal seam strip, and quiet tileable centre;
3 teal door rail, teal condenser edge, teal quiet tileable centre;
4 glass base tile plus the single fixed staircase-shaped diagonal reflection seen in the authority;
5 exact fixed display, exact purple handle front/side/caps, exact ochre grille end caps plus a horizontally tileable middle strip;
6 fixed tiny bolt/hinge pixels and separate transparent wear/chip decals sampled in character and placement from the authority;
7 shelf top, shelf front lip, cream crown top, and crown edge bands.

Every island must explicitly belong to one of four runtime classes: FIXED_CORNER, TILE_X, TILE_Y, or FIXED_DECAL. Protected corners must keep their original texel size. Repeatable centers must be seamless. Fixed decals must have transparent backgrounds. Keep wear sparse, asymmetric, and concentrated where the authority shows it; do not invent rust, dents, ornaments, extra bolts, extra panel seams, or extra labels. Important: all silhouette-changing detail belongs to geometry and must not be painted into this sheet.

Show a compact palette and a 1-pixel padding recommendation outside the islands, but do not place labels inside texture artwork. Make the islands large enough to downsample to an actual low-resolution atlas without losing individual pixels.
'@

$partInvariant = @'
The supplied vaccine-fridge turnaround is the ONLY design authority. The requested component is part of that exact fridge, not a new design. Preserve the authority's proportions, palette, pixel scale, stepped construction and attachment locations. Show the full fridge as a faint registration silhouette behind the isolated component so its position cannot drift. Use orthographic FRONT, RIGHT, TOP and a SECTION through the attachment. Add a 32-pixel construction grid and mark the component origin, bounding box, mating planes and sockets. Neutral clay geometry only except for a small source-color swatch. Distinguish GEOMETRY from TEXTURE ONLY. No products, invented fasteners, rounded modern styling, perspective distortion, decorative noise, logos or watermark.
'@

$shellPartsPrompt = @"
$partInvariant

Produce a PART CONSTRUCTION SHEET for structural group A: main carcass hull, steel side shell, three-stage cream crown, lower condenser housing, plum plinth rail and four feet. Preserve every silhouette step and overhang. The door, cavity, shelves, handle, display and grille may appear only as faint registration outlines. Include enlarged crown and condenser-to-plinth profiles.

HARD NUMERIC AUTHORITY, in model pixels: 32 px = 1 Blender unit; overall height 96; front width 38.75; side depth 36.75; feet z 0..1.125; plinth z 1.125..3.25; condenser z 3.25..19; carcass z 19..87; crown fascia z 87..94; crown roof z 94..96. Use only these numeric labels. Never invent, multiply, round or estimate a number. Where a depth is not supplied, label it UNSPECIFIED. Do not show dimensions such as 50px, 200px or other derived values.
"@

$openingPartsPrompt = @"
$partInvariant

Produce a PART CONSTRUCTION SHEET for structural group B: cream front frame, teal door rails, real glass plane, empty refrigerated cavity, back wall, side walls, floor, ceiling, and one repeated shelf tray with its front lip. Show the exact front-to-back layer stack and exactly four shelf elevations. The outer shell, handle, display and condenser are faint registration outlines only. Do not convert the diagonal glass reflection, seams, highlights, chips or bolts into geometry. Do not add shelf brackets, adjustment tracks, screws, rails behind the shelves, or any attachment absent from the authority.

HARD NUMERIC AUTHORITY, in model pixels: door outer x -15..15 and z 22..82; glass x -12..12 and z 27..79; shelf elevations z 36, 48, 60, 72; cavity front y -15.1 and back y 7.8; glass plane y -15.82. Use only these numeric labels. Never invent, multiply, round or estimate a number. Where a dimension is not supplied, label it UNSPECIFIED.
"@

$hardwarePartsPrompt = @"
$partInvariant

Produce a PART CONSTRUCTION SHEET for structural group C: purple handle with its two mounting blocks, digital 4C display housing, ochre grille frame with repeatable horizontal middle, hinge pixels and attachment sockets. Show fixed-size bounds and mating planes relative to the full fridge. Separate each item's silhouette-changing geometry from its fixed pixel decal. The main carcass and door are faint registration outlines only. Preserve the handle as the simple tall rectangular bar shown in the authority; do not turn it into a U-shaped appliance pull.

HARD NUMERIC AUTHORITY, in model pixels: handle x -18..-15 and z 43..62; grille x -13..13 and z 5..16; display x -5..6 and z 88..93; handle socket [-16.5,-20.4,52.5]; grille socket [0,-18.4,11]; display socket [0,-18.4,90.5]. Use only these numeric labels. Never invent, multiply, round or estimate a number. Where a depth or thickness is not supplied, label it UNSPECIFIED. Do not show relative dimensions such as 1x, 2x or 3x.
"@

$atlasPrompt = @'
Create a clean production PIXEL TEXTURE ATLAS for the exact vaccine fridge in image 1, using image 2 only as a semantic texture-decomposition guide. Image 1 always controls the design, colors, wear character and identifying details. Output only a square atlas canvas: no title, no labels, no arrows, no dimension text, no mockup, no rendered fridge and no surrounding explanation.

Use an exact 4 by 4 grid of equal square cells with straight boundaries and 32 output-pixel transparent gutters between cells. Keep every motif fully inside its cell. Cell order, left-to-right then top-to-bottom:
row 1: quiet seamless cream enamel tile; quiet seamless blue-gray steel tile; quiet seamless deep-teal paint tile; dark-green glass tile with no reflection.
row 2: cream protected corner and two edge strips; steel protected corner and two edge strips; teal protected corner and two edge strips; the single fixed staircase diagonal glass reflection on transparent background.
row 3: ochre grille left end cap; seamless ochre grille horizontal middle; ochre grille right end cap; purple handle front with separate cap pixels on transparent background.
row 4: exact dark-plum digital display reading 4C with orange indicator on transparent background; tiny hinge and bolt decals on transparent background; pale steel shelf top and front-lip bands; cream crown top and edge bands.

Use genuinely hard square low-resolution pixels with nearest-neighbour edges, a small palette sampled from image 1, and three flat baked face-value steps. No gradients, antialiasing, blur, photographic noise, bevel lighting, cast shadows, new symbols, new ornament, checkerboard simulation or watermark-like text. Wear must be sparse and source-faithful. The seamless tiles must join perfectly on opposite edges. This is source material for deterministic cropping and palette quantization, not a presentation sheet.
'@

if ($Pass -in @('All', 'Geometry')) {
  Invoke-SourcePass -Name 'gemini-source-geometry-correction-v2' -Prompt $geometryPrompt -AspectRatio '16:9'
}
if ($Pass -in @('All', 'Textures')) {
  Invoke-SourcePass -Name 'gemini-source-texture-decomposition-v2' -Prompt $texturePrompt -AspectRatio '1:1'
}
if ($Pass -in @('All', 'Parts')) {
  Invoke-SourcePass -Name 'gemini-part-shell-v3' -Prompt $shellPartsPrompt -AspectRatio '16:9'
  Invoke-SourcePass -Name 'gemini-part-opening-v3' -Prompt $openingPartsPrompt -AspectRatio '16:9'
  Invoke-SourcePass -Name 'gemini-part-hardware-v3' -Prompt $hardwarePartsPrompt -AspectRatio '16:9'
}
if ($Pass -in @('All', 'Atlas')) {
  Invoke-SourcePass -Name 'gemini-runtime-atlas-v3' -Prompt $atlasPrompt -AspectRatio '1:1' -ReferencePaths @(
    $authorityPath,
    (Join-Path $lock 'gemini-source-texture-decomposition-v2.jpg')
  )
}
