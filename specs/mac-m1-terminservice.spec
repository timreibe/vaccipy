# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['../main.py'],
             pathex=['specs//'],
             binaries=[('../tools/chromedriver/chromedriver-mac-m1', 'tools/chromedriver/')],
             datas=[('../log/impfterminservice.log', 'log/')],
             hiddenimports=[],
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
          name='mac-m1-terminservice',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='mac-m1-terminservice')
app = BUNDLE(coll,
             name='mac-m1-terminservice.app',
             icon=None,
             bundle_identifier=None)
