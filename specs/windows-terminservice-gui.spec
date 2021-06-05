# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['..\\gui.py'],
             pathex=['specs//'],
             binaries=[('..\\tools\\chromedriver\\chromedriver-windows.exe', 'tools\\chromedriver\\'), ('..\\tools\\gui\\kontaktdaten.ui', 'tools\\gui\\'), ('..\\tools\\gui\\main.ui', 'tools\\gui\\'), ('..\\tools\\gui\\terminsuche.ui', 'tools\\gui\\'), ('..\\tools\\gui\\impfzentren.ui', 'tools\\gui\\'),('..\\images\\spritze.ico', 'images\\')],
             datas=[('../tools/cloudscraper', './cloudscraper/'), ('../version.txt', '.')],
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
          name='windows-terminservice-gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='..\\images\\spritze.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='windows-terminservice-gui')
