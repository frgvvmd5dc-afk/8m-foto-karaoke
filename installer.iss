#define AppName "8M Foto Karaoke"
#define AppVersion "1.0.0"
[Setup]
AppId={{D5AA2EE5-E84D-41C2-B6F9-8BB36D289B0A}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\8M Foto Karaoke
DefaultGroupName=8M Foto Karaoke
OutputDir=dist
OutputBaseFilename=8M-Foto-Karaoke-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
UninstallDisplayName={#AppName}
SetupIconFile=icon.ico
[Files]
Source: "dist\8M-Foto-Karaoke.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\8M Foto Karaoke"; Filename: "{app}\8M-Foto-Karaoke.exe"
Name: "{autodesktop}\8M Foto Karaoke"; Filename: "{app}\8M-Foto-Karaoke.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Desktopverknüpfung erstellen"
[Run]
Filename: "{app}\8M-Foto-Karaoke.exe"; Description: "8M Foto Karaoke starten"; Flags: nowait postinstall skipifsilent
