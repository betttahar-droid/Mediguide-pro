param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$outputRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v5'
$referenceRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-references'
$authority = Join-Path $root 'docs\concept\vaccine-fridge-turnaround-v1.png'
$envPath = Join-Path $root '.env'
$name = 'nano-reference-material-primitives-v5'

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$prompt = @'
Use case: texture-material primitives for a deterministic voxel asset compiler.

Image 1 is the PRIMARY and closest style authority: copy its refrigerator's material language, not its refrigerator design. Image 2 is a quantized diagnostic of the five supplied style references. Image 3 is the vaccine-fridge design/palette authority. Do not redesign Image 3.

Output only a square 4-column by 4-row bitmap of equal touching cells. No gaps, grid lines, labels, letters, captions, objects, perspective, lighting scene, background margin or watermark. Each cell must be an enlarged EXACT 16x16 logical-pixel tile made only of equal hard square blocks with nearest-neighbour edges.

Columns are warm cream enamel, blue-gray steel, deep teal enamel, and dark green glass.
Rows are:
1. quiet flat center field;
2. top-left highlight plus bottom-right shadow edge/corner primitive;
3. sparse rectangular seam / notch / fastener primitive;
4. short panel mark, shelf lip, recessed rail, or staircase reflection primitive.

Copy the primary reference's actual material grammar precisely:
- broad centers are nearly flat, never mottled;
- one median base plus discrete shadow about 0.76x luminance and highlight about 1.21x luminance;
- most deliberate marks are 1 logical pixel thick and 2-6 logical pixels long;
- highlights are cool and desaturated, shadows are blue-plum gray;
- contrast is concentrated at joins, corners, recesses and short rectangular panel marks;
- no random isolated speckles; no camouflage, grain, dirt, watercolor, gradients, dithering clouds, antialiasing, bevel rendering, photorealism or procedural noise;
- top/left bands are light and bottom/right bands dark;
- keep each material family within 4 or 5 colors.

Use Image 3 only for material hues. The sheet is a library of material primitives, never a complete texture atlas and never a render. Exact grid cleanliness and the PRIMARY reference's quiet, chunky pixel construction are more important than decorative richness.
'@

$promptPath = Join-Path $outputRoot "$name-prompt.txt"
[IO.File]::WriteAllText($promptPath, $prompt)
if ($PrepareOnly) { Write-Output "PREPARED=$promptPath"; exit 0 }

$keyLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$uri = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=' + [Uri]::EscapeDataString($apiKey)

$references = @(
  (Join-Path $referenceRoot 'inspo-2.jpg'),
  (Join-Path $referenceRoot 'analysis\reference-material-crops-quantized.png'),
  $authority
)
$parts = [System.Collections.Generic.List[object]]::new()
foreach ($path in $references) {
  $mimeType = if ([IO.Path]::GetExtension($path) -match 'jpe?g') { 'image/jpeg' } else { 'image/png' }
  $parts.Add(@{ inline_data = @{ mime_type = $mimeType; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
}
$parts.Add(@{ text = $prompt })
$body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE') } } | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 300
$imageData = $null
$mime = 'image/png'
foreach ($candidate in $response.candidates) {
  foreach ($part in $candidate.content.parts) {
    if ($part.inlineData) { $imageData = $part.inlineData.data; $mime = $part.inlineData.mimeType }
    if ($part.inline_data) { $imageData = $part.inline_data.data; $mime = $part.inline_data.mime_type }
  }
}
if (-not $imageData) { throw 'Nano Banana returned no image' }
$extension = if ($mime -match 'jpe?g') { '.jpg' } elseif ($mime -match 'webp') { '.webp' } else { '.png' }
$output = Join-Path $outputRoot "$name$extension"
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "SAVED=$output"
