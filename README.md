# N20 TofuPrint

**Open sourced software for the N20 thermal printer**

A Linux and Windows desktop editor that prints directly over USB. No manufacturer app, account, or cloud printing service is required.

[Download](https://github.com/jStimpert0430/N20-TofuPrint/releases) · [Setup & building](docs/SETUP.md) · [GPL v3 or later](LICENSE)

## Features

| | |
| --- | --- |
| **Content** | Multiline text, local images, web image imports, and ten generated patterns |
| **Layout** | Live print preview, font size, alignment, margins, and image brightness |
| **Borders** | Solid, double, dashed, dotted, stars, hearts, and streamers |
| **Paper** | Rectangular and round labels; continuous, gap, and black-mark feed modes |
| **Files** | PNG export and reusable JSON templates |
| **Printing** | Direct USB, three darkness settings, and status diagnostics |

## Printer support

Targets the **N20** reporting USB ID `0483:5602` and model `N20`. Other printers with similar names may use different protocols.

- **203 DPI / 8 dots per mm** nominal resolution.
- **20–50 mm media**, with a maximum **48 mm printable width**.
- **10–300 mm print length**, adjustable in the editor.
- **40 × 30 mm gap labels** are the default and have been tested repeatedly on Linux.
- Round, continuous, and black-mark stock need physical validation. Standard 57/58 mm receipt rolls are too wide.

## Getting started

Download and extract the release for your platform, launch **N20TofuPrint**, select the loaded roll, and choose **Text**, **Image**, or **Patterns**. Review the preview, then print.

**Linux:** x86-64, glibc 2.36+, desktop/OpenGL drivers. A device-specific udev rule is supplied if USB access is denied.

**Windows:** x64 with a WinUSB binding for the N20 interface. The unsigned executable is tested under Wine; native Windows USB printing is not yet verified. See [setup instructions](docs/SETUP.md).

Web access occurs only when importing a link. Images are cached locally; print content is not uploaded. Failed print jobs are not automatically replayed.

## License

**GNU GPL v3 or later**, with a narrow [ImGui linking exception](LICENSE-EXCEPTION). Bundled libraries and fonts retain their own licenses; see [third-party notices](THIRD_PARTY.md).
