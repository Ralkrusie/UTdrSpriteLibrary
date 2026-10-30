# Third-party notices

UTdrSpriteLibrary original code is licensed under GPL-3.0-or-later (see LICENSE). Copyright 2026 UTdrSpriteLibrary contributors. Third-party software retains its original licenses. UI game-derived artwork is separately described in ASSET_NOTICE.md and is not licensed under the project's GPL grant.

| Component | Included version | License / source |
| --- | --- | --- |
| Electron and Chromium/Node dependencies | 45.1.0 win32-x64 | Electron MIT; retain Electron-LICENSE and LICENSES.chromium.html, including bundled dependency notices. https://github.com/electron/electron/tree/v45.1.0 |
| CPython | 3.12.10 | PSF and included third-party licenses. https://www.python.org/downloads/release/python-31210/ |
| Pillow | 12.3.0 | HPND/Pillow license and bundled codec notices in backend/licenses. AVIF plugin excluded from the frozen app. https://github.com/python-pillow/Pillow |
| PyInstaller bootloader | 6.16.0 | GPL with bootloader exception; see copied license. https://github.com/pyinstaller/pyinstaller/tree/v6.16.0 |
| FFmpeg | 7.1 essentials build, gyan.dev, distributed through imageio-ffmpeg 0.7.0 | GPL-3.0-or-later; invoked as a separate executable. Includes statically linked third-party libraries. See RELEASE_PREPARATION.md for corresponding-source status. https://www.gyan.dev/ffmpeg/builds/ |
| UndertaleModLib / UndertaleModTool | 0.9.2.0, commit 03c7048438347799e0717b6e57a9358d000472e0 | GPLv3; compiled/trimming-linked by our dedicated read-only extractor. https://github.com/UnderminersTeam/UndertaleModTool/tree/0.9.2.0 |
| Underanalyzer | UMT submodule 4ff50a866b4c1a7acee8cebe6a56d6a48709b453 | MPL-2.0; exact source snapshot and license collected. https://github.com/UnderminersTeam/Underanalyzer/tree/4ff50a866b4c1a7acee8cebe6a56d6a48709b453 |
| Magick.NET / ImageMagick | Magick.NET 14.16.0 | Apache-2.0 / ImageMagick and delegate-library notices; see collected upstream notices. https://github.com/dlemstra/Magick.NET/tree/14.16.0 |
| Newtonsoft.Json | 13.0.4 | MIT. https://github.com/JamesNK/Newtonsoft.Json/tree/13.0.4 |
| SharpZipLib | 1.4.2 | MIT. https://github.com/icsharpcode/SharpZipLib/tree/v1.4.2 |
| .NET runtime | 10.0.10 win-x64 | MIT and third-party notices, copied from the exact runtime package. https://github.com/dotnet/runtime |

This repository includes the project build scripts, extractor trimming configuration and license notices. Fixed upstream source archives and their SHA-256 manifest are collected separately by tools/release/collect_sources.py; they are not committed to this repository. Source archives are not automatically evidence that every shipped third-party binary is reproducible from those archives. See the explicit pending items in RELEASE_PREPARATION.md.

Do not remove upstream attribution or license texts. The tool's license does not relicense exported game assets. Any future binary release must include the required corresponding sources after the pending binary-source checks are resolved. The current repository publication contains source code and notices only; no Windows runtime ZIP is published.
