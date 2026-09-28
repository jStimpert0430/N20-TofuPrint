# Third-party software

N20 TofuPrint is GPL-3.0-or-later with the additional permission in LICENSE-EXCEPTION. Bundled dependencies retain their own licenses.
The release contains their available license notices in `third-party-licenses/`;
the DejaVu font license is also in `assets/DejaVu-LICENSE.txt`.

| Component | Version | License / upstream source |
| --- | --- | --- |
| CPython | 3.13 | [PSF license and source](https://www.python.org/downloads/source/) |
| Dear ImGui Bundle | 1.92.900 | [MIT; bundled components have their own notices](https://github.com/pthom/imgui_bundle/tree/v1.92.900) |
| Pillow | 12.3.0 | [MIT-CMU / HPND and bundled codec notices](https://pypi.org/project/Pillow/12.3.0/#files) |
| PyUSB | 1.3.1 | [BSD-3-Clause](https://github.com/pyusb/pyusb/tree/1.3.1) |
| libusb-package | 1.0.30.0 | [Apache-2.0 package; libusb LGPL-2.1-or-later](https://pypi.org/project/libusb-package/1.0.30.0/#files) |
| libusb | 1.0.30 | [LGPL-2.1-or-later source](https://github.com/libusb/libusb/releases/tag/v1.0.30) |
| certifi | 2026.7.22 | [MPL-2.0](https://pypi.org/project/certifi/2026.7.22/#files) |
| importlib_resources | 7.1.0 | [Apache-2.0](https://pypi.org/project/importlib_resources/7.1.0/#files) |
| DejaVu Sans | 2.37 | [Bitstream Vera license and public-domain additions](https://dejavu-fonts.github.io/) |
| PyInstaller bootloader | 6.22.3 | [GPL-2.0-or-later with bootloader exception](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3) |

ImGui Bundle includes libraries such as Dear ImGui, GLFW, HelloImGui, and other
extensions. Their notices are provided by its upstream repository and release
license files. No manufacturer executable or printer-driver binary is distributed.

The prebuilt ImGui Bundle includes Dear ImGui Test Engine under its separate
license, which provides free use for qualifying users and public open-source
derivatives. It is not covered by the MIT license. Its complete notice, together
with the other ImGui component notices, is supplied in `licenses/imgui-bundle/`.
The app does not use the test-engine API.
