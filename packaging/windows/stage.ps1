param([string]$Tools = "win-tools")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$stage = Join-Path $root "build\stage"
Remove-Item -Recurse -Force $stage -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $stage, "$stage\tools" | Out-Null
Copy-Item (Join-Path $root "target\release\mukyulauncher.exe") "$stage\MukyuLauncher.exe"
Copy-Item -Recurse (Join-Path $root "assets") "$stage\assets"
Copy-Item -Recurse (Join-Path $root "tools\licenses") "$stage\tools\licenses"
Copy-Item (Join-Path $root "ui\fonts\OFL.txt") "$stage\tools\licenses\Rubik-OFL.txt"
Copy-Item (Join-Path $root "LICENSE") "$stage\LICENSE.txt"
foreach ($rel in @("thtk\bin\thdat.exe", "pc98\bin\pmd_render.exe", "pc98\bin\mdt_render.exe")) {
    $src = Join-Path $Tools $rel
    if (-not (Test-Path $src)) { throw "Missing native tool: $rel" }
    $dst = Join-Path "$stage\tools" $rel
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $src $dst
}
if (Test-Path (Join-Path $Tools "licenses")) { Copy-Item -Recurse -Force (Join-Path $Tools "licenses\*") "$stage\tools\licenses" }
Copy-Item (Join-Path $root "build\pdfium\pdfium.dll") "$stage\pdfium.dll"
if (Test-Path (Join-Path $root "build\pdfium\licenses")) { Copy-Item (Join-Path $root "build\pdfium\licenses\*") "$stage\tools\licenses" }
Write-Host "Staged to $stage"
