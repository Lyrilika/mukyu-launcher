#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef Arch
  #define Arch "x64"
#endif
#ifndef Stage
  #define Stage "..\..\build\stage"
#endif
#define AppName "Mukyu Launcher"

[Setup]
AppId={{1E7864F2-D894-462E-A249-08AE2EEE2B08}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Mukyu Launcher contributors
DefaultDirName={autopf}\{#AppName}
UsePreviousAppDir=yes
UsePreviousTasks=yes
UsePreviousPrivileges=yes
CloseApplications=no
RestartApplications=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MukyuLauncher.exe
OutputDir=..\..\dist
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
#if Arch == "arm64"
OutputBaseFilename=Mukyu_Launcher_Setup_arm64
ArchitecturesAllowed=arm64
ArchitecturesInstallIn64BitMode=arm64
MinVersion=10.0.16299
#elif Arch == "x86"
OutputBaseFilename=Mukyu_Launcher_Setup_x86
MinVersion=10.0.14393
#else
OutputBaseFilename=Mukyu_Launcher_Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.14393
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\MukyuLauncher.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MukyuLauncher.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\MukyuLauncher.exe"; WorkingDir: "{app}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\MukyuLauncher.exe"; WorkingDir: "{app}"; Flags: nowait runasoriginaluser; Check: ShouldRelaunch

[Code]
function HasSwitch(const Name: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount do
    if CompareText(ParamStr(I), Name) = 0 then
      Result := True;
end;

function ShouldRelaunch(): Boolean;
begin
  Result := HasSwitch('/RELAUNCH');
end;

function InitializeSetup(): Boolean;
var
  Waited: Integer;
begin
  Result := True;
  Waited := 0;
  while CheckForMutexes('MukyuLauncherRunning') do
  begin
    if WizardSilent then
    begin
      if Waited >= 60000 then
      begin
        Result := False;
        Exit;
      end;
      Sleep(250);
      Waited := Waited + 250;
    end
    else if MsgBox('Mukyu Launcher is running. Close it, then click OK to continue.', mbInformation, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
      Exit;
    end;
  end;
end;
