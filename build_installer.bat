@echo off
REM AIOperator Installer Builder using Inno Setup
REM Requires Inno Setup: https://jrsoftware.org/isinfo.php

echo ============================================
echo    AIOperator Installer Builder
echo ============================================

REM Check if dist folder exists
if not exist "dist\AIOperator" (
    echo ERROR: dist\AIOperator not found!
    echo Run build.bat first to create the executable.
    exit /b 1
)

REM Check for Inno Setup
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %ISCC% (
    echo ERROR: Inno Setup not found!
    echo Download from: https://jrsoftware.org/isinfo.php
    exit /b 1
)

echo Building installer...
%ISCC% installer.iss

if errorlevel 1 (
    echo.
    echo INSTALLER BUILD FAILED!
    exit /b 1
)

echo.
echo ============================================
echo    Installer Created Successfully!
echo ============================================
echo.
echo Installer location: Output\AIOperator_Setup.exe
echo.

pause
