param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$keyLine = Get-Content -LiteralPath (Join-Path $root '.env') |
  Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()

function Invoke-FridgeSheet($name, $prompt, $referencePaths) {
  $parts = [System.Collections.Generic.List[object]]::new()
  foreach ($relative in $referencePaths) {
    $path = if ([IO.Path]::IsPathRooted($relative)) { $relative } else { Join-Path $root $relative }
    $ext = [IO.Path]::GetExtension($path).ToLowerInvariant()
    $mime = if ($ext -eq '.gif') { 'image/gif' } elseif ($ext -eq '.png') { 'image/png' } else { 'image/jpeg' }
    $parts.Add(@{ inline_data = @{ mime_type = $mime; data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path)) } })
  }
  $parts.Add(@{ text = $prompt })
  $body = @{ contents = @(@{ parts = $parts }); generationConfig = @{ responseModalities = @('IMAGE') } } |
    ConvertTo-Json -Depth 8 -Compress
  $uri = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent?key=' +
    [Uri]::EscapeDataString($apiKey)
  $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $body -TimeoutSec 180
  $blob = $null
  foreach ($candidate in $response.candidates) {
    foreach ($part in $candidate.content.parts) {
      if ($part.inlineData) { $blob = $part.inlineData.data; break }
      if ($part.inline_data) { $blob = $part.inline_data.data; break }
    }
    if ($blob) { break }
  }
  if (-not $blob) { throw "Gemini returned no image for $name" }
  $out = Join-Path $root "docs\concept\$name.png"
  [IO.File]::WriteAllBytes($out, [Convert]::FromBase64String($blob))
  Write-Output "SAVED=$out"
}

$refs = @(
  'C:\Users\mansour\Downloads\inspo 1.jpg',
  'C:\Users\mansour\Downloads\inspo 4.jpg',
  'C:\Users\mansour\Downloads\big inspo 3.jpg',
  'C:\Users\mansour\Downloads\inspo 3.gif',
  'C:\Users\mansour\Downloads\inspo 2.jpg',
  'docs\concept\vaccine-fridge-turnaround-v1.png',
  'docs\concept\vaccine-fridge-remodel-v7-acceptance.png'
)

$proportions = @'
Create a strict production PROPORTIONS SHEET for the exact approved vaccine fridge in the supplied turnaround. The current Blender render is only a failed comparison, not design authority. Show perfectly consistent FRONT, RIGHT SIDE, TOP and ISOMETRIC views of one identical fridge. Add normalized dimension lines using total BODY WIDTH = 1.00: total height, depth, crown height and overhang, condenser base height, plinth height, outer frame widths, glass opening width/height, side-panel taper at bottom and top, inset depths, handle dimensions and offsets, display dimensions and offsets, grille dimensions, shelf thickness and four shelf elevations. Include a component stacking diagram and silhouette overlay comparing the desired reference against the current Blender render. Preserve the approved tall low-poly design exactly; do not redesign it. Empty cavity and four shelves, no products. Geometry only: neutral clay colors, no decorative texture, no perspective distortion in orthographic views. Values must be internally consistent and readable.
'@

$textures = @'
Create a strict production TEXTURE SHEET for the exact approved vaccine fridge. Show flat orthographic texture layouts, not beauty renders: RIGHT STEEL SIDE PANEL, LEFT SIDE PANEL, CREAM OUTER FRAME vertical and horizontal strips, TEAL INNER DOOR FRAME strips, GLASS PANE, CONDENSER HOUSING, GRILLE, DISPLAY and HANDLE. Use crisp nearest-neighbour low-resolution pixel art matching the supplied inspiration and approved turnaround. Each panel must show exact pixel dimensions, constant texel density, three baked face-value steps, restrained 1-2 pixel bolts, asymmetric white chipped-paint clusters concentrated at exposed lower corners, paired dark/light seams, sparse scratches, quiet centres, and one clean staircase glass reflection. Explicitly diagram fixed four-corner cells, repeatable edge strips, repeatable blank centres and fixed decal islands for adaptive one-, two- and three-door widths. Avoid repeated mirrored wear, random noise, gradients, blur and perspective. Provide a palette swatch and UV padding guidance. This sheet will be manually recreated, so make every panel large and readable.
'@

Invoke-FridgeSheet 'vaccine-fridge-nano-proportions-v2' $proportions $refs
Invoke-FridgeSheet 'vaccine-fridge-nano-textures-v2' $textures $refs
