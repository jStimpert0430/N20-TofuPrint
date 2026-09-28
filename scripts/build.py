# SPDX-License-Identifier: GPL-3.0-or-later WITH LicenseRef-ImGui-Bundle-exception
"""Build a self-contained executable on the current platform."""
from importlib import metadata
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
licenses = root/'third-party-licenses'
licenses.mkdir(exist_ok=True)
for name in ['imgui-bundle','Pillow','pyusb','libusb-package','certifi','importlib_resources']:
    dist = metadata.distribution(name)
    target = licenses/name
    target.mkdir(exist_ok=True)
    for entry in dist.files or []:
        if any(word in str(entry).lower() for word in ('license','copying','notice')):
            path = Path(dist.locate_file(entry))
            if path.is_file():
                dest = target/str(entry).replace('\\','_').replace('/','_')
                shutil.copy2(path,dest)
    (target/'VERSION.txt').write_text(f'{name} {dist.version}\n',encoding='utf-8')
subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','N20TofuPrint.spec'],cwd=root,check=True)
