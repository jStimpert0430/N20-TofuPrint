# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

datas = [('assets', 'assets'), ('LICENSE', '.'), ('LICENSE-EXCEPTION', '.'), ('licenses', 'licenses'), ('THIRD_PARTY.md', '.')]
datas += collect_data_files('imgui_bundle', includes=['assets/**', 'LICENSE'])
datas += collect_data_files('certifi')
binaries = collect_dynamic_libs('imgui_bundle') + collect_dynamic_libs('libusb_package')
for package in ['imgui-bundle','Pillow','pyusb','libusb-package','certifi','importlib_resources']:
    datas += copy_metadata(package)
extra = Path('third-party-licenses')
if extra.exists():
    datas.append((str(extra), 'third-party-licenses'))
a = Analysis(['app.py'], pathex=[], binaries=binaries, datas=datas,
             hiddenimports=['usb.backend.libusb1','libusb_package'],
             excludes=['tkinter','pytest','IPython','matplotlib'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='N20TofuPrint',
          debug=False, strip=False, upx=False, console=True)
