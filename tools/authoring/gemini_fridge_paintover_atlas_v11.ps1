$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$out = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\paintover-v11'
$guide = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v10\adaptive-decals-v10-layout-guide.png'

$prompt = @'
Use case: stylized-concept
Asset type: source decal atlas derived from approved geometry-aware texture paintovers

Images 1 and 2 are the approved texture PAINTOVER authorities for this exact vaccine fridge. They define which surface marks make sense and how the retro pixel style treats those functions. Image 3 is a SPATIAL GUIDE ONLY. Do not copy its grey frames or crosshairs.

Generate exactly one square 4-column by 4-row atlas board on a perfectly uniform pure-magenta #FF00FF background. No grid, captions, labels, text, frames, crosshairs, shadows, full appliance, or watermark. Each cell contains exactly one isolated straight-on decal centered with a wide magenta margin. Do not draw perspective panels or complete material tiles. Extract and regularize only the specific functional marks seen in the paintovers.

Cells left-to-right, top-to-bottom:
1 cream frame top-left stepped corner fitting
2 cream frame bottom-right stepped corner fitting
3 cream short pressed horizontal seam
4 cream roof/crown corner cap
5 blue-grey side access-panel horizontal seam with two end fasteners
6 blue-grey connected fastener pair
7 deep-teal base access-panel seam
8 deep-teal base corner cap
9 blue-green wide diagonal staircase glass reflection
10 blue-green compact staircase glass glint
11 pale shelf front-lip highlight segment
12 purple-and-steel shelf end cap
13 dark control display bezel with a quiet empty center; no text
14 purple handle vertical highlight with dark end caps
15 warm-ochre ventilation grille module with six horizontal openings
16 tiny amber caution plate made from abstract bars; absolutely no readable text

Mandatory style: match the paintovers' exact chunky PS1/pixel-art language; hard square nearest-neighbour pixels; 2-4 flat colours per decal; orthogonal clusters and stair steps; deliberate asymmetry; no gradients, antialiasing, blur, glow, dirt, scratches, rust, random speckle, letters, logos, fake 3D thickness, or rectangular backing tile except where the functional fitting itself is a plate. Every motif must stay entirely within the central 50% of its cell so the compiler can create a safe gutter.
'@
$promptPath = Join-Path $out 'paintover-atlas-v11-prompt.txt'
[IO.File]::WriteAllText($promptPath, $prompt)
$envPath = Join-Path $root '.env'
$keyLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$uri = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=' + [Uri]::EscapeDataString($apiKey)
$references = @(
  (Join-Path $out 'paintover-iso-nano-v11.png'),
  (Join-Path $out 'paintover-front-nano-v11.png'),
  $guide
)
$parts = [System.Collections.Generic.List[object]]::new()
foreach ($path in $references) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing reference: $path" }
  $parts.Add(@{ inline_data = @{ mime_type = 'image/png'; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
}
$parts.Add(@{ text = $prompt })
$body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE'); imageConfig = @{ aspectRatio = '1:1'; imageSize = '1K' } } } | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 300
$imageData = $null
foreach ($candidate in $response.candidates) {
  foreach ($part in $candidate.content.parts) {
    if ($part.inlineData) { $imageData = $part.inlineData.data }
    if ($part.inline_data) { $imageData = $part.inline_data.data }
  }
}
if (-not $imageData) { throw 'Nano Banana 2 returned no atlas image' }
$output = Join-Path $out 'paintover-atlas-v11-source.png'
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "MODEL=gemini-3.1-flash-image"
Write-Output "SAVED=$output"
