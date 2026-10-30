# Third-party notices

UTdrSpriteLibrary original code is licensed under GPL-3.0-or-later (see LICENSE). Copyright 2026 UTdrSpriteLibrary contributors. Third-party software retains its original licenses. UI game-derived artwork is separately described in ASSET_NOTICE.md and is not licensed under the project's GPL grant.

| Component | Version used by applicable builds | License / source |
| --- | --- | --- |
| Electron and Chromium/Node dependencies | 45.1.0 win32-x64 | Electron MIT; retain Electron-LICENSE and LICENSES.chromium.html, including bundled dependency notices. https://github.com/electron/electron/tree/v45.1.0 |
| CPython | 3.12.10 | PSF and included third-party licenses. https://www.python.org/downloads/release/python-31210/ |
| Pillow | 12.3.0 | HPND/Pillow license and bundled codec notices in backend/licenses. AVIF plugin excluded from the frozen app. https://github.com/python-pillow/Pillow |
| PyInstaller bootloader | 6.16.0 | GPL with bootloader exception; see copied license. https://github.com/pyinstaller/pyinstaller/tree/v6.16.0 |
| FFmpeg | 7.1-utdr1, built by tools/ffmpeg/build.py | LGPL-2.1-or-later; separate executable, no external codec libraries. Generated VERSION metadata only; configuration and compiler record in backend/licenses. https://github.com/FFmpeg/FFmpeg/tree/n7.1 |
| UndertaleModLib / UndertaleModTool | 0.9.2.0, commit 03c7048438347799e0717b6e57a9358d000472e0 | GPLv3; built from the pinned source and trimming-linked by our read-only extractor. Only build-time Git provenance generation is replaced with the fixed commit. https://github.com/UnderminersTeam/UndertaleModTool/tree/0.9.2.0 |
| Underanalyzer | UMT submodule 4ff50a866b4c1a7acee8cebe6a56d6a48709b453 | MPL-2.0; exact source snapshot and license collected. https://github.com/UnderminersTeam/Underanalyzer/tree/4ff50a866b4c1a7acee8cebe6a56d6a48709b453 |
| Magick.NET / ImageMagick | Magick.NET 14.16.0 | Apache-2.0 / ImageMagick and delegate-library licenses; complete native notice and signed/unsigned PE provenance are in licenses/third-party/Magick.Native-*. https://github.com/dlemstra/Magick.NET/tree/14.16.0 |
| Newtonsoft.Json | 13.0.4 | MIT. https://github.com/JamesNK/Newtonsoft.Json/tree/13.0.4 |
| SharpZipLib | 1.4.2 | MIT. https://github.com/icsharpcode/SharpZipLib/tree/v1.4.2 |
| .NET runtime | 10.0.10 win-x64 | MIT and third-party notices, copied from the exact runtime package. https://github.com/dotnet/runtime |

The macOS/Linux ZIP-library candidates omit the game extractor, UMT, .NET, Magick.NET and its dependencies. Their FFmpeg recipe is `tools/ffmpeg/build_posix.py`. The table above also covers the full Windows edition.

Original upstream licenses are retained in `licenses/third-party`; runtime builds also include Electron/Chromium and backend license files. `tools/release/collect_sources.py` collects fixed source archives and SHA-256 hashes separately from Git. Native source layout and rebuild references are in [NATIVE_SOURCES.md](docs/NATIVE_SOURCES.md). Windows prereleases are distributed with matching project and upstream source archives on [GitHub Releases](https://github.com/Ralkrusie/UTdrSpriteLibrary/releases).
