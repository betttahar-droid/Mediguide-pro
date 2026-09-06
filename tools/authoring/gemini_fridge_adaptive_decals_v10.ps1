param([switch]$PrepareOnly)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$out = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v10'
$research = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-research-v7'
python (Join-Path $PSScriptRoot 'prepare_nano_adaptive_decals_v10.py')
if ($LASTEXITCODE -ne 0) { throw 'Failed to prepare Nano guide' }
if ($PrepareOnly) { exit 0 }

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
  (Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\recipe-v10\view-iso.png'),
  (Join-Path $out 'adaptive-decals-v10-layout-guide.png')
)
$parts = [System.Collections.Generic.List[object]]::new()
foreach ($path in $references) {
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing reference: $path" }
  $mime = if ([IO.Path]::GetExtension($path) -match 'jpe?g') { 'image/jpeg' } else { 'image/png' }
  $parts.Add(@{ inline_data = @{ mime_type = $mime; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
}
$parts.Add(@{ text = [IO.File]::ReadAllText((Join-Path $out 'adaptive-decals-v10-prompt.txt')) })
$body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE'); imageConfig = @{ aspectRatio = '1:1'; imageSize = '1K' } } } | ConvertTo-Json -Depth 10 -Compress
$response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 300
$imageData = $null
foreach ($candidate in $response.candidates) {
  foreach ($part in $candidate.content.parts) {
    if ($part.inlineData) { $imageData = $part.inlineData.data }
    if ($part.inline_data) { $imageData = $part.inline_data.data }
  }
}
if (-not $imageData) { throw 'Nano Banana 2 returned no image' }
$output = Join-Path $out 'adaptive-decals-v10-source.png'
[IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($imageData))
Write-Output "MODEL=gemini-3.1-flash-image"
Write-Output "SAVED=$output"
