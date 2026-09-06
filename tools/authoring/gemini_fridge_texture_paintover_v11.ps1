param(
  [ValidateSet('front','iso')][string]$View = 'iso'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$research = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-research-v7'
$out = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\paintover-v11'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$target = Join-Path $out "raw\view-$View-decals-0.png"
$companionView = if ($View -eq 'iso') { 'front' } else { 'iso' }
$companion = Join-Path $out "raw\view-$companionView-decals-0.png"

$prompt = @"
Use case: precise-object-edit
Asset type: geometry-locked texture paintover used as the visual authority for a procedural decal compiler

Images 1-5 are the sole STYLE authorities. Image 6 is the EDIT TARGET ($View view) and defines the exact canvas, camera, silhouette, proportions, geometry, shelf count, handle shape, part positions, and background. Image 7 is a companion geometry view for understanding only.

Change ONLY the surface treatment of Image 6. Return exactly one $View-view image. Preserve Image 6 pixel-for-pixel wherever no deliberate surface mark is needed. Do not change the silhouette, camera, object scale or position, crown, roof, frame thickness, opening, shelves, base, plinth, handle, background, or number of parts.

Texture the existing surfaces in the reference's chunky retro PS1/pixel-art style:
- cream enamel: restrained stepped corner catches and short pressed seams aligned with actual frame and roof edges;
- blue-grey cabinet: two or three purposeful service-panel joints on the visible side, short crown seams, and fixed fastener groups only where panels meet;
- deep-teal base: a readable warm-ochre ventilation grille, one service-panel break, and a tiny caution plate beside the grille;
- dark glass/cavity: two broad blue-green stair-step reflections that stay inside the opening and never cover shelf readability;
- shelves: pale front-lip accents and darker underside end caps aligned to each real shelf;
- top control zone: one dark display, a small row of status lamps, and compact edge seams;
- purple handle: one pale vertical catch and dark end caps, fitted exactly within the existing handle geometry.

Texture density must match Images 1-5: bold clustered marks separated by large quiet areas. Every mark must explain construction, material, contact, reflection, ventilation, or controls. No random dirt or generic scatter.

Mandatory invariants: hard square pixels; nearest-neighbour look; limited 25-40 colour appearance; no antialiasing, gradients, blur, bloom, smooth noise, text, logos, extra props, cast shadows, environment lighting, geometry edits, added protrusions, missing shelves, or changed background. Do not redraw the object. Paint only onto the existing faces of Image 6.
"@
$promptPath = Join-Path $out "paintover-$View-prompt.txt"
[IO.File]::WriteAllText($promptPath, $prompt)

$envPath = Join-Path $root '.env'
$keyLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$uri = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=' + [Uri]::EscapeDataString($apiKey)
$references = @(
  'C:\Users\mansour\Downloads\inspo 1.jpg',
  'C:\Users\mansour\Downloads\inspo 4.jpg',
  'C:\Users\mansour\Downloads\big inspo 3.jpg',
  'C:\Users\mansour\Downloads\inspo 2.jpg',
  (Join-Path $research 'inspo-3-gif-samples.png'),
  $target,
  $companion
)
$parts = [System.Collections.Generic.List[object]]::new()
foreach ($path in $references) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing reference: $path" }
  $mime = if ([IO.Path]::GetExtension($path) -match 'jpe?g') { 'image/jpeg' } else { 'image/png' }
  $parts.Add(@{ inline_data = @{ mime_type = $mime; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
}
$parts.Add(@{ text = $prompt })
$body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE'); imageConfig = @{ aspectRatio = '4:5'; imageSize = '1K' } } } | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 300
$imageData = $null
foreach ($candidate in $response.candidates) {
  foreach ($part in $candidate.content.parts) {
    if ($part.inlineData) { $imageData = $part.inlineData.data }
    if ($part.inline_data) { $imageData = $part.inline_data.data }
  }
}
if (-not $imageData) { throw 'Nano Banana 2 returned no paintover image' }
$output = Join-Path $out "paintover-$View-nano-v11.png"
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "MODEL=gemini-3.1-flash-image"
Write-Output "SAVED=$output"
