# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

a = Analysis(['../main.py'],
             pathex=['./specs'],
             binaries=[('../tools/chromedriver/chromedriver-linux-64', 'tools/chromedriver/')],
             datas=[('../tools/cloudscraper', './cloudscraper/'), ('../version.txt', '.')],
             hiddenimports=['cloudscraper'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='linux-64-terminservice',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='linux-64-terminservice')
