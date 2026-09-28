# Setup and building

## Installation

Download the archive for your platform, extract it, and launch `N20TofuPrint` or `N20TofuPrint.exe`. Python is included in the executable.

### Linux x86-64

Requires glibc 2.36 or newer, a desktop session, and OpenGL graphics drivers. If necessary, mark the executable as runnable:

```sh
chmod +x N20TofuPrint
./N20TofuPrint
```

If USB access is denied, install the supplied `70-n20-tofuprint.rules` in `/etc/udev/rules.d/`, reload udev rules, and reconnect the printer. Run the application as your regular user. The native file picker uses an available desktop dialog utility such as Zenity or KDialog.

### Windows x64

The application uses libusb and requires a **WinUSB** binding for the N20 USB interface. If the printer is not accessible, use [Zadig](https://zadig.akeo.ie/) to select the device with USB ID **0483:5602** and install WinUSB. Verify the ID carefully; changing another device's driver can disable that device. This binding can replace its normal Windows printer-driver access.

Install the [Microsoft Visual C++ x64 runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe) if Windows reports a missing MSVCP140.dll.

The Windows executable is unsigned. Its GUI and software tests are checked under Wine; USB printing on native Windows has not yet been verified.

## Use

1. Load paper and select the matching roll preset and feed mode.
2. Choose **Text**, **Image**, or **Patterns**; adjust the preview and border.
3. Click **Print one label** or **Print receipt**.

Web imports accept direct HTTP(S) image links and ordinary pages containing images. They do not run page scripts or access login-only content. Network requests occur only when importing a link; labels are not uploaded. Imports are cached locally, and failed imports preserve the existing label. Keep cached images with your saved templates.

Release settings, imports, and logs are stored under `%LOCALAPPDATA%/N20TofuPrint` on Windows or `$XDG_DATA_HOME/N20TofuPrint` on Linux (default `~/.local/share/N20TofuPrint`). Print jobs are never automatically replayed after a failed transfer.

## Build from source

Use Python 3.13 or newer:

```sh
python -m venv .venv
# Activate .venv using your platform's shell.
python -m pip install -r requirements.txt -r requirements-build.txt
python -m unittest discover -v
python app.py
python scripts/build.py
```

Build on the target operating system. The Linux release is built in Debian 12; the Windows release is built with Windows Python. `Dockerfile.linux` provides the Linux build environment. `--smoke-test` opens eight GUI frames and exits without accessing the printer.

## License

Application code is licensed under **GNU GPL v3 or later**. See [LICENSE](../LICENSE) and [third-party notices](../THIRD_PARTY.md) for bundled libraries and fonts.
