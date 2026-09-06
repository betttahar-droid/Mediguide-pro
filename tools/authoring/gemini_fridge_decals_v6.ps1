param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$outputRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v6'
$referenceRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-references'
$authority = Join-Path $root 'docs\concept\vaccine-fridge-turnaround-v1.png'
$current = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\source-true-preview.png'
$name = 'nano-fixed-decals-v6'
$envPath = Join-Path $root '.env'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$prompt = @'
Use case: stylized-concept.
Asset type: isolated fixed-size pixel decals for a scalable retro voxel refrigerator.

Image 1 is the PRIMARY material-style authority. Image 2 summarizes the supplied style references. Image 3 is the refrigerator design authority. Image 4 is the accepted current refrigerator; do not redesign it.

Output one square 4-column by 4-row decal source board on a perfectly uniform pure magenta #FF00FF background. The background must fill every unused pixel with no shadows, glow, texture, checkerboard, border, labels, writing or gutters. Each cell is equal and contains exactly one isolated decal centered with a large empty magenta safety margin on every side. No decal may touch a cell boundary.

Cells left-to-right, top-to-bottom:
1 cream top-left enamel corner chip; cream top-right corner chip; cream bottom-left notch; cream bottom-right notch.
2 blue-gray steel short dark panel mark; steel short light catch mark; steel two-pixel seam interruption; steel small square fastener.
3 deep-teal upper-left door-rail chip; teal upper-right rail notch; teal lower-left chip; teal lower-right recessed-corner mark.
4 dark-green staircase glass reflection; pale-steel shelf-lip end cap; warm-cream crown seam accent; ochre grille corner wear.

Style rules copied from Image 1:
- nearest-neighbour hard square pixels with no antialiasing or gradients;
- each motif reads at 16x16 logical pixels;
- individual marks are 1 logical pixel thick and 2-6 logical pixels long;
- connected clusters stay within 2x6 logical pixels;
- use only 2-4 flat colors inside each decal;
- asymmetrical, deliberate rectangular marks; never random speckle, grime, rust clouds or broad surface patches;
- preserve Image 3's cream, steel, teal, glass and ochre hues;
- decal only: never draw a refrigerator, panel, material tile, frame, lighting example, text, logo or watermark.

The magenta margin and exact isolated silhouettes are mandatory because a deterministic compiler will key out #FF00FF, quantize colors and add protected atlas padding.
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
  $authority,
  $current
)
$parts = [System.Collections.Generic.List[object]]::new()
foreach ($path in $references) {
  $mime = if ([IO.Path]::GetExtension($path) -match 'jpe?g') { 'image/jpeg' } else { 'image/png' }
  $parts.Add(@{ inline_data = @{ mime_type = $mime; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
}
$parts.Add(@{ text = $prompt })
$body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE') } } | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 300
$imageData = $null
$imageMime = 'image/png'
foreach ($candidate in $response.candidates) {
  foreach ($part in $candidate.content.parts) {
    if ($part.inlineData) { $imageData = $part.inlineData.data; $imageMime = $part.inlineData.mimeType }
    if ($part.inline_data) { $imageData = $part.inline_data.data; $imageMime = $part.inline_data.mime_type }
  }
}
if (-not $imageData) { throw 'Nano Banana returned no decal image' }
$extension = if ($imageMime -match 'jpe?g') { '.jpg' } elseif ($imageMime -match 'webp') { '.webp' } else { '.png' }
$output = Join-Path $outputRoot "$name$extension"
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "SAVED=$output"
