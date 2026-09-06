$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
if (-not (Test-Path -LiteralPath $blender)) { throw 'Blender 5.2 was not found.' }

Push-Location $root
try {
  node test\voxel-fridge.mjs
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $blender --background --python tools\authoring\render_fridge_variant_parity.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  python tools\authoring\compare_fridge_variant_parity.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  & $blender --background --python tools\authoring\render_fridge_authority_variants.py
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
