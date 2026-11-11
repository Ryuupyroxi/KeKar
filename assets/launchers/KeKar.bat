@echo off
rem KeKar launcher (Windows)
rem
rem Double-click this file to open KeKar. It works from any drive letter and
rem leaves nothing behind on the computer except the KeKarData folder on this
rem drive.
setlocal
set "HERE=%~dp0"

if not exist "%HERE%KeKar_Windows\KeKar.exe" (
  echo.
  echo  KeKar was not found on this drive.
  echo  Look for the folder named KeKar_Windows and try again.
  echo.
  pause
  exit /b 1
)

start "" "%HERE%KeKar_Windows\KeKar.exe"
endlocal
