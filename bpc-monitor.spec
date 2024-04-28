# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from site import getusersitepackages
from os import environ
#import shutil

PACKAGE_SITE= getusersitepackages()
print ("Site packages", PACKAGE_SITE)
#config_dest = environ.get('USERPROFILE') + '\\.bpc\\config.ini'
a = Analysis(
    ['bpc-monitor.py'],
    pathex=[''],
    binaries=[],
    datas=[('.\Vision130.py', '.'), ('.\\ui\\main.ui', '.\\ui\\')],
    hiddenimports = ['pyi_splash'],
    #hiddenimports=['pyi_splash','pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt6', 'pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt6', 'pyqtgraph.imageview.ImageViewTemplate_pyqt6'],
    hookspath=[f'{PACKAGE_SITE}/pyupdater/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

splash = Splash('.\\icons\\splash-screen.jpg',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(10, 30),
                text_size=10,
                text_color='black')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    splash,                   # <-- both, splash target
    splash.binaries,          # <-- and splash binaries
    name='bpc-monitor.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    icon=".\\icons\\main.ico",
    entitlements_file=None,
)
#shutil.copyfile('config.ini', '{0}/config.ini'.format(DISTPATH))