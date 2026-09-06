$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$blenderCandidates = @(
  'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
  'C:\Program Files\Blender Foundation\Blender 4.4\blender.exe',
  'C:\Program Files\Blender Foundation\Blender 4.0\blender.exe'
)
$blender = $blenderCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $blender) { throw 'Blender 4.0 or newer was not found.' }

python (Join-Path $PSScriptRoot 'measure_fridge_texture_style.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python (Join-Path $PSScriptRoot 'build_nano_fridge_materials_v5.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python (Join-Path $PSScriptRoot 'extract_fridge_adaptive_atlas.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $blender --background --python (Join-Path $PSScriptRoot 'build_fridge_source_true.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
