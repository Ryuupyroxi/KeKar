; packaging/windows/KeKar_Installer.nsi
; Builds KeKar_Setup_<version>.exe — copies the portable folder to
; %LOCALAPPDATA%\KeKar for faster daily use. The USB build remains the
; primary, install-free path; this installer is optional.
!define APPNAME "KeKar"
!define COMPANY "KeKar Rental Properties"
!define VERSION "0.1.0"

; Installer, uninstaller and shortcut icons. ${__FILEDIR__} is this script's
; own directory, so the path holds wherever makensis is invoked from. The
; same .ico is staged into the Windows package root by
; tools/make_usb_package.py and the shortcuts read it from there.
!define MUI_ICON "${__FILEDIR__}\kekar.ico"
!define MUI_UNICON "${__FILEDIR__}\kekar.ico"

Name "${APPNAME} ${VERSION}"
OutFile "KeKar_Setup_${VERSION}.exe"
InstallDir "$LOCALAPPDATA\KeKar"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "KeKar_Windows\*.*"
  CreateShortcut "$DESKTOP\KeKar.lnk" "$INSTDIR\KeKar.exe" "" "$INSTDIR\kekar.ico"
  CreateShortcut "$SMPROGRAMS\KeKar.lnk" "$INSTDIR\KeKar.exe" "" "$INSTDIR\kekar.ico"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\KeKar.lnk"
  Delete "$SMPROGRAMS\KeKar.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
