# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for AIOperator.

Build with: pyinstaller --clean aioperator.spec
"""

import sys
from pathlib import Path

block_cipher = None

# Get project root
project_root = Path(SPECPATH)

# Analysis
a = Analysis(
    ['run.pyw'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include .env.example as template
        ('.env.example', '.'),
        # Include docs
        ('docs', 'docs'),
        # Include README
        ('README.md', '.'),
    ],
    hiddenimports=[
        # PyQt5 modules
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        # Selenium
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.firefox.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        # OpenAI
        'openai',
        # APScheduler
        'apscheduler.schedulers.background',
        'apscheduler.jobstores.sqlalchemy',
        'apscheduler.executors.pool',
        # Cryptography
        'cryptography.fernet',
        # SQLite
        'sqlite3',
        # Webdriver manager
        'webdriver_manager.chrome',
        'webdriver_manager.firefox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test modules
        'pytest',
        'pytestqt',
        # Exclude dev tools
        'black',
        'mypy',
        'pylint',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AIOperator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if (project_root / 'assets' / 'icon.ico').exists() else None,
)

# Collect all files
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AIOperator',
)
