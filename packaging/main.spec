# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['typing_extensions', 
                 'langchain-openai',
                 'langgraph', 
                 'openai', 
                 'google-genai',
                 'google',
                 'nltk',
                 'sentence_transformers',
                 'scikit-learn',
                 'langchain-community',
                 'pydantic',
                 'pydantic.deprecated.decorator',
                 'tiktoken_ext.openai_public',
                 'tiktoken_ext',
                 'chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2'
                 ]

tmp_ret = collect_all('chromadb')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

import customtkinter
import os
customtkinter_dir = os.path.dirname(customtkinter.__file__)
datas.append((customtkinter_dir, 'customtkinter'))
datas.append(('assets/icons/app.ico', 'assets/icons'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='AI_NovelGenerator_V1.4.4',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icons/app.ico']
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_NovelGenerator_V1.4.4'
)


