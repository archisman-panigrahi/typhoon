!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!ifndef PRODUCT_VERSION
  !define PRODUCT_VERSION "dev"
!endif

!ifndef APP_BUILD_DIR
  !error "APP_BUILD_DIR is required (path to packaged app directory)"
!endif

!ifndef OUTPUT_DIR
  !define OUTPUT_DIR "."
!endif

!define APP_NAME "Typhoon"
!define PUBLISHER "archisman-panigrahi"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

!ifndef LAUNCHER_EXE_REL
  !define LAUNCHER_EXE_REL "${APP_NAME}.exe"
!endif

!ifdef APP_ICON_ICO
  !define MUI_ICON "${APP_ICON_ICO}"
  !define MUI_UNICON "${APP_ICON_ICO}"
!endif

Name "${APP_NAME}"
OutFile "${OUTPUT_DIR}\${APP_NAME}-${PRODUCT_VERSION}-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
RequestExecutionLevel highest

SetCompressor /SOLID lzma

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\${APP_NAME}"
  SetShellVarContext current

  SetOutPath "$INSTDIR"
  File /r "${APP_BUILD_DIR}\*.*"

  StrCpy $0 "$INSTDIR\${LAUNCHER_EXE_REL}"
  IfFileExists "$0" launcher_found 0
  StrCpy $0 "$INSTDIR\${APP_NAME}\${APP_NAME}.exe"
  IfFileExists "$0" launcher_found 0
  StrCpy $0 "$INSTDIR\typhoon\${APP_NAME}.exe"
  IfFileExists "$0" launcher_found 0
  StrCpy $0 "$INSTDIR\typhoon\typhoon.exe"
  IfFileExists "$0" launcher_found 0
  MessageBox MB_ICONSTOP "Launcher EXE not found. Set LAUNCHER_EXE_REL or ensure the build output contains ${APP_NAME}.exe."
  Abort

  launcher_found:

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$0"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$0"

  WriteRegStr SHCTX "${UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr SHCTX "${UNINSTALL_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr SHCTX "${UNINSTALL_KEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr SHCTX "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr SHCTX "${UNINSTALL_KEY}" "DisplayIcon" "$0"
  WriteRegStr SHCTX "${UNINSTALL_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD SHCTX "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD SHCTX "${UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
