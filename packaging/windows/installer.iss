#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "Mukyu Launcher"
#define Stage "..\..\build\stage"

[Setup]
AppId={{6F1C2B7A-4C0E-4B61-9E0B-5A3C7D2E8F10}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppName}.ico
OutputDir=..\..\dist
OutputBaseFilename=Mukyu_Launcher_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "icon.ico"; DestDir: "{app}"; DestName: "{#AppName}.ico"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\runtime\bin\MukyuLauncher.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\{#AppName}.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\runtime\bin\MukyuLauncher.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; IconFilename: "{app}\{#AppName}.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\bin\MukyuLauncher.exe"; Parameters: """{app}\app\main.py"""; WorkingDir: "{app}\app"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
