param([switch]$AtlasOnly)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$keyLine = Get-Content -LiteralPath (Join-Path $root '.env') |
  Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$model = 'gemini-3.1-flash-image'
$uri = "https://generativelanguage.googleapis.com/v1beta/models/$model`:generateContent?key=" + [Uri]::EscapeDataString($apiKey)

function Invoke-Authority($name, $prompt) {
  $refs = @('docs\concept\vaccine-fridge-turnaround-v1.png')
  if ($name -like '*atlas-v5') { $refs += 'docs\concept\vaccine-fridge-atlas-v4.png' }
  $parts = [System.Collections.Generic.List[object]]::new()
  foreach ($relative in $refs) {
    $path = Join-Path $root $relative
    $parts.Add(@{ inline_data = @{ mime_type = 'image/png'; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
  }
  $parts.Add(@{ text = $prompt })
  $body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE') } } |
    ConvertTo-Json -Depth 10 -Compress
  $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 240
  $image = $null
  $text = [System.Collections.Generic.List[string]]::new()
  foreach ($candidate in $response.candidates) {
    foreach ($part in $candidate.content.parts) {
      if ($part.text) { $text.Add($part.text) }
      if ($part.inlineData) { $image = $part.inlineData.data }
      if ($part.inline_data) { $image = $part.inline_data.data }
    }
  }
  if (-not $image) {
    $reason = ($response.candidates | ForEach-Object { $_.finishReason }) -join ','
    $feedback = $response.promptFeedback | ConvertTo-Json -Depth 5 -Compress
    throw "Nano Banana returned no image for $name finish=$reason feedback=$feedback"
  }
  $imagePath = Join-Path $root "docs\concept\$name.png"
  [IO.File]::WriteAllBytes($imagePath, [Convert]::FromBase64String($image))
  Write-Output "SAVED=$imagePath"
}

$blueprint = @'
Act as a production CAD drafter. The FIRST supplied image, vaccine-fridge-turnaround-v1, is the only visual design authority. The second image explains texture layering only.

Produce a clean orthographic blueprint for exactly that fridge using this FINAL IMMUTABLE coordinate table. Copy these numbers verbatim; do not infer, replace, duplicate or leave placeholders:
GRID 32 px = 1 Blender unit.
OVERALL [-22,-18,0] to [22,15,96]. BODY [-20,-14,4] to [20,14,84]. PLINTH [-20,-13,0] to [20,13,4]. CONDENSER [-20,-14,4] to [20,14,18]. CARCASS [-20,-14,18] to [20,14,84]. CROWN_LOWER [-22,-15,84] to [22,15,88]. CROWN_MIDDLE [-20,-13,88] to [20,13,92]. CROWN_TOP [-18,-11,92] to [18,11,96]. OUTER_FRAME [-18,-15,18] to [18,-12,84]. DOOR_FRAME [-15,-17,22] to [15,-15,81]. GLASS [-12,-17.25,25] to [12,-17,78]. HANDLE [-20,-18,43] to [-17,-15,61]. DISPLAY [0,-18,83] to [11,-15,88]. GRILLE [-15,-15,8] to [15,-14,15]. SHELVES X [-14,14], Y [-10,10], Z [29,41,53,65], thickness 2.
Show FRONT, RIGHT, BACK, TOP and ISO of one identical model. Print the coordinate table large and readable. Include checks: crown width=44, body width=40, total height=96. No placeholders, products, redesign, vague ratios or decorative texture.
'@

$atlas = @'
Act as a senior pixel-texture artist and atlas engineer. The supplied vaccine-fridge-turnaround-v1 is the only visual authority. Produce a square nearest-neighbour RGBA texture atlas, not a board and not a render. Use an EXACT 4 by 4 grid of equal cells with no labels, gutters, borders or text. Cell coordinates are column,row starting at 0.
row0: cream tile; steel tile; teal tile; dark-green glass with one staircase reflection.
row1: cream protected edges/corners; steel protected edges/corners; teal protected edges/corners; fixed display reading exactly 4C with orange indicator.
row2: gold grille horizontally tileable center; gold grille fixed end caps; fixed purple handle; fixed bolts and hinges on transparent background.
row3: cream chipped-paint decals transparent; steel corner wear transparent; teal corner wear transparent; transparent empty cell.

Match the reference palette and exact character: warm ivory with baked light/mid/dark face values, pale blue-gray steel panels, deep teal door and base, aubergine handle/feet, ochre-gold grille, dark green glass. Use hard square pixels only, no antialiasing, no smooth gradients. Put fixed corner chips, bolts and seams only within 8 px protected margins. Keep panel centers seamless/tileable and quiet. Make grille left/right ends fixed and its middle horizontally tileable. Keep the display as one fixed decal reading exactly 4C with orange indicator. Keep one fixed diagonal staircase glass reflection. No labels inside atlas rectangles, no products, no logo, no watermark.

The generated bitmap itself must be exactly the atlas artwork.
'@

if (-not $AtlasOnly) {
  Invoke-Authority 'vaccine-fridge-blueprint-v4' $blueprint
  Invoke-Authority 'vaccine-fridge-atlas-v4' $atlas
} else {
  $atlas5 = $atlas + @'

The SECOND supplied image is a rejected draft atlas. Keep its exact 4x4 cell placement, but correct only these mismatches against the first turnaround: simplify cream and teal corner cells to plain industrial strips with sparse 1-2 pixel bolts and tiny asymmetric chips; remove ornamental stepped maze-like borders; make the grille saturated ochre-gold with dark plum slots; keep quiet centers; keep the purple handle compact and solid. Do not move cells or introduce labels.
'@
  Invoke-Authority 'vaccine-fridge-atlas-v5' $atlas5
}
