# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/lazxwe/Documents/GitHub/Tool_ASR Inputer/src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/lazxwe/Documents/GitHub/Tool_ASR Inputer/.venv/lib/python3.12/site-packages/opencc', 'opencc')],
    hiddenimports=['opencc', 'numpy', 'sounddevice', 'pyperclip', 'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'pynput', 'pynput.keyboard', 'pynput.mouse', 'torch', 'transformers', 'safetensors', 'safetensors.torch', 'huggingface_hub', 'timeit', 'http.cookies', 'unittest.mock', 'queue', 'threading', 'pynput.keyboard._darwin', 'pynput.mouse._darwin', 'pystray._darwin'],
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
    name='Tool_ASR_Inputer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Tool_ASR_Inputer',
)
