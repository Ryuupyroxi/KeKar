; packaging/windows/KeKar_Installer.nsi
; Builds KeKar_Setup_<version>.exe — copies the portable folder to
; %LOCALAPPDATA%\KeKar for faster daily use. The USB build remains the
; primary, install-free path; this installer is optional.
!define APPNAME "KeKar"
!define COMPANY "KeKar Rental Properties"
!define VERSION "0.1.0"

Name "${APPNAME} ${VERSION}"
OutFile "KeKar_Setup_${VERSION}.exe"
InstallDir "$LOCALAPPDATA\KeKar"
RequestExecutionLevel user
SetCompressor /SOLID lzma

Page directory
Page instfiles
UninstPage instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "KeKar_Windows\*.*"
  CreateShortcut "$DESKTOP\KeKar.lnk" "$INSTDIR\KeKar.exe"
  CreateShortcut "$SMPROGRAMS\KeKar.lnk" "$INSTDIR\KeKar.exe"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\KeKar.lnk"
  Delete "$SMPROGRAMS\KeKar.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
