# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for the Astrologically Intelligent desktop bundle."""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

datas = [
    ("licenses", "licenses"),
    ("THIRD_PARTY_PROVENANCE.json", "."),
    ("ACKNOWLEDGMENTS.md", "."),
    ("static", "static"),
    ("scripts", "scripts"),
    ("mcp_servers", "mcp_servers"),
    ("services/hwfit/data", "services/hwfit/data"),
    ("config", "config"),
    (".env.example", "."),
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("uvicorn"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AstrologicallyIntelligent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="static/icon.ico",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AstrologicallyIntelligent",
)
