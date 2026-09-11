#define MyAppName "Amigurumi AI"
#define MyAppVersion "0.7.3"
#define MyAppPublisher "Amigurumi AI"
#define MyAppExeName "AmigurumiAI.exe"

[Setup]
AppId={{A4A4F9D5-5C3B-4A5B-9A4B-8A9C2C9D5E01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Amigurumi AI
PrivilegesRequired=lowest
DefaultGroupName=Amigurumi AI
OutputDir=..\dist\installer
OutputBaseFilename=AmigurumiAI-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\AmigurumiAI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\AmigurumiAI-Updater.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Amigurumi AI"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Amigurumi AI"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Avvia Amigurumi AI"; Flags: nowait postinstall
