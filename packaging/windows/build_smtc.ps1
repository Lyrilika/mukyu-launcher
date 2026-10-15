param([string]$OutputDirectory = "$PSScriptRoot/../../tools/windows")
$ErrorActionPreference = 'Stop'
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio C++ Build Tools and a Windows 10/11 SDK are required.' }
$devcmd = Join-Path $vs 'Common7\Tools\VsDevCmd.bat'
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$out = (Resolve-Path $OutputDirectory).Path
$source = Join-Path $PSScriptRoot '../../tools/windows/smtc.cpp'
$build = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
New-Item -ItemType Directory $build | Out-Null
try {
    $command = "`"$devcmd`" -arch=x64 -host_arch=x64 && cl /nologo /std:c++20 /EHsc /O2 /MT /LD /DWIN32_LEAN_AND_MEAN /DWINVER=0x0A00 /D_WIN32_WINNT=0x0A00 /Fo`"$build\smtc.obj`" `"$source`" /link /OUT:`"$out\mukyu_smtc.dll`" /IMPLIB:`"$build\smtc.lib`" windowsapp.lib runtimeobject.lib ole32.lib user32.lib"
    & cmd.exe /d /s /c "`"$command`""
    if ($LASTEXITCODE -ne 0) { throw "SMTC bridge build failed ($LASTEXITCODE)" }
} finally {
    Remove-Item -Recurse -Force $build
}
