$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$blenderCandidates = @(
  'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe',
  'C:\Program Files\Blender Foundation\Blender 4.4\blender.exe',
  'C:\Program Files\Blender Foundation\Blender 4.0\blender.exe'
)
$blender = $blenderCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $blender) { throw 'Blender 4.0 or newer was not found.' }

Push-Location $root
try {
  & $blender --background --python (Join-Path $PSScriptRoot 'render_fridge_orthographic_gates.py')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  node (Join-Path $root 'test\compare-fridge-orthographic-gates.mjs')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

  node (Join-Path $root 'test\source-true-fridge.mjs')
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
  Pop-Location
}
