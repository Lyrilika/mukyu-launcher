param([string]$Msys = "C:\msys64", [string]$What = "all")
$ErrorActionPreference = "Stop"

$bash = Join-Path $Msys "usr\bin\bash.exe"
if (-not (Test-Path $bash)) {
    Write-Host "MSYS2 was not found at $Msys."
    Write-Host "Install it first (winget install MSYS2.MSYS2), or pass -Msys <folder>."
    exit 1
}

$script = Join-Path $PSScriptRoot "build_tools_msys2.sh"
$env:CHERE_INVOKING = "1"
if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") {
    $env:MSYSTEM = "CLANGARM64"
    $env:CC = "clang"
    $env:CXX = "clang++"
    $packages = "mingw-w64-clang-aarch64-clang mingw-w64-clang-aarch64-cmake mingw-w64-clang-aarch64-ninja"
} else {
    $env:MSYSTEM = "UCRT64"
    $packages = "mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja"
}
$cmd = 'pacman -S --needed --noconfirm git make flex bison ' + $packages + ' && ' +
       'bash "$(cygpath -u ''' + $script + ''')" ' + $What
& $bash -lc $cmd
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed (see the output above)."; exit $LASTEXITCODE }
Write-Host "Done. thdat.exe -> tools\thtk\bin, pmd_render.exe / mdt_render.exe -> tools\pc98\bin"
