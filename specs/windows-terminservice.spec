# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

# cloudscraper setup:
import os 
import cloudscraper
user_agent_path = os.path.join(os.path.dirname(cloudscraper.__file__),"user_agent") 



a = Analysis(['..\\main.py'],
             pathex=['specs//'],
             binaries=[('..\\tools\\chromedriver\\chromedriver-windows.exe', 'tools\\chromedriver\\')],
             datas=[(user_agent_path, 'cloudscraper\\user_agent')],
             hiddenimports=['plyer.platforms.win.notification', 'cloudscraper'],
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
          name='windows-terminservice',
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
               name='windows-terminservice')
