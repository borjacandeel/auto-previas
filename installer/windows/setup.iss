; Inno Setup Script para AutoPrevias (Windows x64)
; Desarrollado para Radical Records

#ifndef AppVersion
#define AppVersion "1.0.0"
#endif

[Setup]
AppId={{C789218F-A362-4C61-9E89-E8652D027F11}
AppName=AutoPrevias
AppVersion={#AppVersion}
AppVerName=AutoPrevias {#AppVersion}
AppPublisher=Radical Records
AppPublisherURL=mailto:radicalrecordsvlc@gmail.com
AppSupportURL=mailto:radicalrecordsvlc@gmail.com
DefaultDirName={autopf}\AutoPrevias
DefaultGroupName=AutoPrevias
AllowNoIcons=yes
OutputDir=..\..\dist
OutputBaseFilename=AutoPrevias-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\AutoPrevias.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\AutoPrevias.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\AutoPrevias"; Filename: "{app}\AutoPrevias.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{cm:UninstallProgram,AutoPrevias}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AutoPrevias"; Filename: "{app}\AutoPrevias.exe"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoPrevias.exe"; Description: "{cm:LaunchProgram,AutoPrevias}"; Flags: nowait postinstall skipifsilent
