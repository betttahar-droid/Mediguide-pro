param(
  [ValidateSet('All', 'Target', 'Kit', 'RetroTarget', 'RetroKit')]
  [string]$Pass = 'All',
  [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$lock = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v3'
$retroLock = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\nano-banana-v4'
$styleRoot = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\style-references'
$authority = Join-Path $root 'docs\concept\vaccine-fridge-turnaround-v1.png'
$currentRender = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\variants\authority-1door-pixel-v6.png'
$retroCurrentRender = Join-Path $root 'docs\reference-lock\vaccine-fridge-v1\variants\authority-1door-nano-v3.png'
$envPath = Join-Path $root '.env'

$keyLine = Get-Content -LiteralPath $envPath |
  Where-Object { $_ -match '^GEMINI_API_KEY=.+' } | Select-Object -First 1
if (-not $keyLine) { throw 'Missing GEMINI_API_KEY in .env' }
$apiKey = $keyLine.Substring($keyLine.IndexOf('=') + 1).Trim()
$model = 'gemini-3.1-flash-image'
$uri = "https://generativelanguage.googleapis.com/v1beta/models/$model`:generateContent?key=" +
  [Uri]::EscapeDataString($apiKey)

New-Item -ItemType Directory -Force -Path $lock | Out-Null
New-Item -ItemType Directory -Force -Path $retroLock | Out-Null

$styleReferences = @(
  (Join-Path $styleRoot 'inspo-1.jpg'),
  (Join-Path $styleRoot 'inspo-4.jpg'),
  (Join-Path $styleRoot 'big-inspo-3.jpg'),
  (Join-Path $styleRoot 'inspo-3.gif'),
  (Join-Path $styleRoot 'inspo-2.jpg')
)

function Get-MimeType([string]$Path) {
  switch ([IO.Path]::GetExtension($Path).ToLowerInvariant()) {
    '.gif' { return 'image/gif' }
    '.png' { return 'image/png' }
    '.webp' { return 'image/webp' }
    default { return 'image/jpeg' }
  }
}

function Invoke-NanoTexturePass {
  param(
    [string]$Name,
    [string]$Prompt,
    [string[]]$ReferencePaths,
    [string]$OutputRoot = $lock
  )

  $promptPath = Join-Path $OutputRoot "$Name-prompt.txt"
  $responsePath = Join-Path $OutputRoot "$Name-response.txt"
  [IO.File]::WriteAllText($promptPath, $Prompt)
  if ($PrepareOnly) {
    Write-Output "PREPARED=$promptPath"
    return
  }

  $parts = [System.Collections.Generic.List[object]]::new()
  foreach ($path in $ReferencePaths) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing reference: $path" }
    $parts.Add(@{ inline_data = @{
      mime_type = Get-MimeType $path
      data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($path))
    } })
  }
  $parts.Add(@{ text = $Prompt })
  $body = @{
    contents = @(@{ parts = $parts })
    generationConfig = @{ responseModalities = @('IMAGE') }
  } | ConvertTo-Json -Depth 10 -Compress

  try {
    $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' `
      -Body $body -TimeoutSec 300
  }
  catch {
    $detail = $_.ErrorDetails.Message
    if ($detail) { throw "Nano Banana request failed for $Name`: $detail" }
    throw
  }

  $imageData = $null
  $imageMime = 'image/png'
  $responseText = [System.Collections.Generic.List[string]]::new()
  foreach ($candidate in $response.candidates) {
    foreach ($part in $candidate.content.parts) {
      if ($part.text) { $responseText.Add($part.text) }
      if ($part.inlineData) {
        $imageData = $part.inlineData.data
        $imageMime = $part.inlineData.mimeType
      }
      if ($part.inline_data) {
        $imageData = $part.inline_data.data
        $imageMime = $part.inline_data.mime_type
      }
    }
  }
  if (-not $imageData) {
    $finish = ($response.candidates | ForEach-Object { $_.finishReason }) -join ','
    throw "Nano Banana returned no image for $Name (finish=$finish)"
  }

  $extension = switch -Regex ($imageMime) {
    'jpe?g' { '.jpg'; break }
    'webp' { '.webp'; break }
    default { '.png' }
  }
  $outputPath = Join-Path $OutputRoot "$Name$extension"
  [IO.File]::WriteAllBytes($outputPath, [Convert]::FromBase64String($imageData))
  [IO.File]::WriteAllText($responsePath, ($responseText -join [Environment]::NewLine))
  Write-Output "SAVED=$outputPath"
}

$targetPrompt = @'
Use case: style-transfer.
Asset type: production appearance target for a scalable low-poly voxel prop.

Images 1-5 are the ONLY texture-style authority. Image 6 is the ONLY fridge design and palette authority. Image 7 is the current Blender render and therefore the edit target. Change its surface treatment only. Preserve Image 7's geometry, dimensions, camera, object pose, shelf count, empty interior, handle, display, grille, glass, silhouette, and black background exactly.

Correct the material treatment to match Images 1-5 at the refrigerator's actual logical grid of roughly 39 pixels wide by 96 pixels tall. The reference style is crisp low-resolution voxel pixel art: mostly quiet flat faces, strong face-aware value steps, narrow panel seams, and sparse deliberate clusters. Use many small readable details instead of a few large cloudy patches.

Pixel-scale contract:
- all surface pixels are hard squares with nearest-neighbour edges;
- ordinary marks are 1 logical pixel; small clusters are 2x2 or 2x3; no material patch may exceed 4x4 logical pixels;
- use a restrained 6-10 color palette across each material family;
- top-facing planes are one flat value step lighter, right-facing planes one flat value step darker;
- add thin 1-pixel paired highlight/shadow seams around panels and shelf lips;
- keep broad centers quiet, with sparse tiny chips, fasteners and short scratches at corners and exposed edges;
- preserve the exact cream, blue-gray steel, deep teal, purple, ochre and dark-green identity from Image 6;
- keep glass readable with one narrow staircase highlight, not a smooth reflection.

Avoid large camouflage blobs, watercolor mottling, photographic dirt, gradients, blur, antialiasing, smooth plastic, outline-only cartoon rendering, dense noise, excessive rust, text other than the existing display, extra geometry, or a redesigned fridge.

Output exactly one clean isometric render of the corrected fridge on the same black background. No comparison panel, labels, arrows, border, caption, watermark, or extra objects.
'@

$kitPrompt = @'
Use case: stylized-concept.
Asset type: source bitmap for a deterministic voxel-material compiler.

Images 1-5 are the ONLY texture-style authority. Image 6 is the ONLY fridge palette/design authority. Image 7 is the approved Nano Banana appearance target. Produce only a square texture-source bitmap. This is not a render, not a texture explanation, and not a presentation board.

Draw an exact 4 columns by 4 rows arrangement of equal square cells. Cells touch with straight invisible boundaries: no gutters, grid lines, frames, labels, letters, numbers, arrows, captions, checkerboard, or background outside the cells. Every cell is an enlarged nearest-neighbour view of an EXACT 8x8 LOGICAL PIXEL motif: precisely eight equal square blocks across and eight down. Never draw finer subpixels inside a block.

Cell order, left-to-right and then top-to-bottom:
row 1: seamless warm-ivory enamel microtile; seamless blue-gray steel microtile; seamless deep-teal enamel microtile; seamless dark-green glass microtile.
row 2: cream face-aware edge/corner band; steel face-aware edge/corner band; teal face-aware edge/corner band; glass staircase-reflection motif.
row 3: cream tiny chip cluster; steel tiny bolt/scratch cluster; teal tiny chip cluster; pale-steel shelf-lip band.
row 4: cream crown edge band; steel panel-seam band; teal door-recess band; ochre grille bar with dark-plum slot.

Style contract from Images 1-5:
- crisp hard square pixels, limited palette, no antialiasing, blur, smooth gradients, photographic noise or bevel rendering;
- ordinary details occupy one logical pixel, clusters at most 2x3 pixels, never broad cloudy patches;
- row-1 microtiles have quiet centers and low-frequency sparse variation, but clearly readable contrast;
- opposite edges of row-1 cells use matching colors so they can repeat;
- bands use one-pixel highlight next to one-pixel shadow;
- wear is sparse, asymmetric, and limited to exposed corners;
- no whole object, no fridge silhouette, no handles, no display glyph, no logo, no products, no text, no watermark.

The bitmap itself must be the artwork. Exact cell placement and exact 8x8 logical block size matter more than decorative richness.
'@

$retroTargetPrompt = @'
Use case: style-transfer.
Asset type: final retro pixel-art appearance target for a scalable voxel game prop.

Images 1-5 are the ONLY texture-style authority. Image 6 is the ONLY fridge design authority. Image 7 is the accepted v3 Blender render and the edit target. Preserve Image 7's exact geometry, proportions, camera, pose, shelf count, empty interior, handle, display, grille, glass, silhouette, and black background. Change only rendering and surface treatment.

Push the accepted direction distinctly further toward handcrafted RETRO VOXEL PIXEL ART. It must look like a deliberately low-resolution game sprite rendered from a 3D model, not like a smooth modern 3D render with texture noise.

Retro style contract:
- use a strict 12-16 color master palette for the whole object;
- use hard square pixels and chunky 2x2 screen-pixel clusters with absolutely no smooth gradients or soft material transitions;
- convert lighting into three discrete value bands: bright top/left, mid front, dark right/bottom;
- give important panel boundaries paired one-pixel highlight and shadow lines;
- use staircase diagonals and stepped corners rather than smooth diagonal antialiasing;
- add sparse purposeful 1-pixel bolts, 2-pixel chips, short scratches, tiny corner notches, shelf-lip bands, glass reflection steps, and grille accents;
- keep broad centers calm; detail density should be highest at edges, recesses, joints and corners;
- strengthen dark teal/plum outlines and the warm cream/ochre contrast while preserving the design palette;
- retain the exact existing display and grille identity.

Every visible texture mark must align to one consistent logical pixel grid. Individual details must stay small; do not replace them with large cloudy material patches. Avoid photorealism, smooth bevel shading, ambient-occlusion fog, tiny high-frequency noise, watercolor mottling, dense polka dots, rounded geometry, extra parts, text, labels, borders or comparison layouts.

Output exactly one clean isometric fridge render on the same black background, filling the same frame. No caption, arrows, watermark, UI or extra objects.
'@

$retroKitPrompt = @'
Use case: stylized-concept.
Asset type: retro voxel microtexture source for a deterministic compiler.

Images 1-5 are the ONLY texture-style authority. Image 6 is the fridge palette/design authority. Image 7 is the accepted retro appearance target. Output only a square source bitmap, never a render or explanatory sheet.

Create an exact 4 columns by 4 rows arrangement of equal touching cells with invisible boundaries. No gutters, grid lines, labels, text, arrows, frames, checkerboard or surrounding background. Each cell represents an enlarged EXACT 16x16 LOGICAL PIXEL motif. Draw only equal hard square blocks; never add detail smaller than one logical block.

Cells left-to-right, top-to-bottom:
row 1: warm-ivory enamel quiet microtile; blue-gray steel quiet microtile; deep-teal enamel quiet microtile; dark-green glass quiet microtile.
row 2: cream top/left highlight and bottom/right shadow corner; steel corner band; teal recessed-frame corner; staircase glass reflection.
row 3: sparse cream chips and one fastener; steel scratch/bolt cluster; teal chips/notches; pale-steel shelf highlight/shadow lip.
row 4: cream crown trim; paired steel panel seam; paired teal door trim; ochre grille bar with dark-plum slot.

Use one strict retro palette with three discrete face values per material. Texture marks are one logical pixel, with occasional two-pixel pairs and no connected cluster larger than 2x2. Keep row-1 centers mostly flat: at most six accent pixels in each 16x16 tile. Opposite edges in row 1 must use the same base color. Use stronger contrast than the previous sheet, but no gradients, blur, antialiasing, photographic noise, dithering clouds, repeated polka dots, whole objects, handles, displays, letters, logos or watermarks.

The bitmap itself must be the artwork. Exact 16x16 logical scale and clean cells are more important than decorative complexity.
'@

$targetPath = Join-Path $lock 'nano-style-target-v3.png'
if ($Pass -in @('All', 'Target')) {
  Invoke-NanoTexturePass -Name 'nano-style-target-v3' -Prompt $targetPrompt `
    -ReferencePaths ($styleReferences + @($authority, $currentRender))
}
if ($Pass -in @('All', 'Kit')) {
  if (-not $PrepareOnly -and -not (Test-Path -LiteralPath $targetPath)) {
    $jpgTarget = [IO.Path]::ChangeExtension($targetPath, '.jpg')
    if (Test-Path -LiteralPath $jpgTarget) { $targetPath = $jpgTarget }
  }
  Invoke-NanoTexturePass -Name 'nano-microtexture-kit-v3' -Prompt $kitPrompt `
    -ReferencePaths ($styleReferences + @($authority, $targetPath))
}

$retroTargetPath = Join-Path $retroLock 'nano-retro-style-target-v4.png'
if ($Pass -eq 'RetroTarget') {
  Invoke-NanoTexturePass -Name 'nano-retro-style-target-v4' -Prompt $retroTargetPrompt `
    -ReferencePaths ($styleReferences + @($authority, $retroCurrentRender)) `
    -OutputRoot $retroLock
}
if ($Pass -eq 'RetroKit') {
  if (-not $PrepareOnly -and -not (Test-Path -LiteralPath $retroTargetPath)) {
    $jpgTarget = [IO.Path]::ChangeExtension($retroTargetPath, '.jpg')
    if (Test-Path -LiteralPath $jpgTarget) { $retroTargetPath = $jpgTarget }
  }
  Invoke-NanoTexturePass -Name 'nano-retro-microtexture-kit-v4' -Prompt $retroKitPrompt `
    -ReferencePaths ($styleReferences + @($authority, $retroTargetPath)) `
    -OutputRoot $retroLock
}
