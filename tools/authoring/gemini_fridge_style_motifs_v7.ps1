param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$outputRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v7'
$researchRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-research-v7'
$authority = Join-Path $root 'docs\concept\vaccine-fridge-turnaround-v1.png'
$current = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\source-true-preview.png'
$name = 'nano-style-motifs-v7'
$envPath = Join-Path $root '.env'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$prompt = @'
Use case: stylized-concept.
Asset type: source motifs for a deterministic retro pixel-art 3D material/decal compiler.

Images 1-4 are the supplied still-image style authorities. Image 5 is a three-frame sample from the supplied animated style authority. Study their chunky mechanical pixel clusters, stepped corner highlights, dark seam caps, blocky glass reflections, restrained panel markings, and limited material ramps. Image 6 defines the vaccine refrigerator design. Image 7 is the accepted refrigerator geometry; preserve it and generate surface motifs only.

Output exactly one square 4-column by 4-row source board. The entire unused background must be perfectly uniform pure magenta #FF00FF: no cell borders, labels, shadows, texture, checkerboard, writing, guide lines, or watermark. Every equal cell contains exactly one isolated, connected, hard-edged pixel motif centered with a wide magenta margin. Each motif should occupy roughly 35-55% of its cell so it remains readable after reduction to 16x16 logical pixels.

Cells left-to-right, top-to-bottom:
1 steel top-left stepped highlight; steel bottom-right shadow corner; steel short double panel seam; steel compact square fastener.
2 cream enamel top-left corner catch; cream enamel bottom-right notch; cream crown double seam; cream short edge interruption.
3 deep-teal door top-left stair reflection; deep-teal door bottom-right recessed corner; blue-green glass diagonal staircase glint; pale-steel shelf end-cap cluster.
4 blue-gray side-service triple dash; pale-blue side-panel catch pair; warm-ochre grille corner cap; restrained purple handle end-cap.

Mandatory style constraints:
- true nearest-neighbour square pixels; absolutely no antialiasing, gradients, blur or soft shadows;
- only 2-4 flat colors per motif, sampled in spirit from the reference families;
- connected rectangular clusters, typically 2-8 logical pixels long and 1-3 pixels thick;
- deliberate asymmetry and stair steps; broad empty centers;
- no random speckles, dirt, rust, scratches, clouds, material panels, complete appliances, fake depth, text or logos;
- the motif alone sits on magenta; never paint a rectangular base tile behind it.

The compiler will key out magenta, quantize the result to locked cream/steel/teal/glass/ochre/purple palettes, enforce margins, and reject disconnected noise. Silhouette clarity is more important than illustration detail.
'@

$promptPath = Join-Path $outputRoot "$name-prompt.txt"
[IO.File]::WriteAllText($promptPath, $prompt)
if ($PrepareOnly) { Write-Output "PREPARED=$promptPath"; exit 0 }

$keyLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$uri = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=' + [Uri]::EscapeDataString($apiKey)
$references = @(
  'C:\Users\mansour\Downloads\inspo 1.jpg',
  'C:\Users\mansour\Downloads\inspo 4.jpg',
  'C:\Users\mansour\Downloads\big inspo 3.jpg',
  'C:\Users\mansour\Downloads\inspo 2.jpg',
  (Join-Path $researchRoot 'inspo-3-gif-samples.png'),
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
if (-not $imageData) { throw 'Nano Banana returned no motif image' }
$extension = if ($imageMime -match 'jpe?g') { '.jpg' } elseif ($imageMime -match 'webp') { '.webp' } else { '.png' }
$output = Join-Path $outputRoot "$name$extension"
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "SAVED=$output"
