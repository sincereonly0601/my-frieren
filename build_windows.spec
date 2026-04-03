# -*- mode: python ; coding: utf-8 -*-
# Windows 目錄版打包：產物在 dist/葬送的魔法使夢工廠/
# 建置：pip install -r requirements-build.txt
#       pyinstaller --noconfirm build_windows.spec
# 須與 main.py 同目錄存在 assets/（含 cg、bgm、portraits 等）。

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets"), ("whim_questions.json", ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 略過本遊戲未使用之標準庫／常見肥大套件，可省數 MB（勿加入 ssl：hashlib 可能依賴）。
    excludes=[
        "tkinter",
        "unittest",
        "test",
        "pydoc",
        "pydoc_data",
        "ensurepip",
        "venv",
        "lib2to3",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "IPython",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="葬送的魔法使夢工廠",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="葬送的魔法使夢工廠",
)
