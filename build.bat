@echo off
REM AIOperator Build Script for Windows
REM Builds the application into a standalone executable

echo ============================================
echo    AIOperator Build Script
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

REM Check PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous build
echo Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

REM Build
echo Building AIOperator...
pyinstaller --clean aioperator.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    exit /b 1
)

echo.
echo ============================================
echo    Build Complete!
echo ============================================
echo.
echo Executable location: dist\AIOperator\AIOperator.exe
echo.
echo To create installer, run: build_installer.bat
echo.

pause
