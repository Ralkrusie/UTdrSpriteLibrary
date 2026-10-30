# Windows 构建

在仓库根目录操作。构建目标为 Windows x64；依赖必须明确获取，不引用本项目历史发布包。所有输出目录使用新名称。

## 环境与依赖

- Python 3.12.10；Python 依赖版本固定在 `requirements-build.txt`。
- .NET SDK 10.0.302，目标运行时 10.0.10；首次构建需联网，NuGet 缓存位于 `vendor/nuget`。
- Visual Studio C++ x64 构建工具（本次 MSVC 19.51.36252）和 MSYS2＋GNU Make，用于编译精简 FFmpeg；MSYS2 内执行 `pacman -S make`。
- [Electron 45.1.0](https://github.com/electron/electron/releases/tag/v45.1.0)：将 `electron-v45.1.0-win32-x64.zip` 保存为 `vendor/electron/electron-verified.zip`，官方 `SHASUMS256.txt` 放在同目录。
- [UMT 0.9.2.0](https://github.com/UnderminersTeam/UndertaleModTool/releases/tag/0.9.2.0)：将 `UTMT_CLI_v0.9.2.0-Windows.zip` 保存为 `vendor/umt/cli-download.zip`，解压到 `vendor/umt/0.9.2.0`，其中直接包含 `UndertaleModLib.dll`。ZIP 的 SHA-256 必须为 `e7573e45d107be34f81f955c6e4afc3c7c8f2628e5a6f307a871e3825b3dfb40`。

构建脚本校验上述归档；两项 UI 资源已在 `assets/ui`，无需完整游戏包或字体图集。将配套来源包中的 `upstream-sources` 内容放入 `vendor/release-sources`，或使用下方收集命令获取。

## 构建

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python tools/release/collect_sources.py
.venv\Scripts\python tools/release/verify_native.py
.venv\Scripts\python tools/ffmpeg/build.py --msys2 "C:/msys64" --vcvars "C:/Program Files/Microsoft Visual Studio/18/Community/VC/Auxiliary/Build/vcvars64.bat" --out releases/ffmpeg-new
.venv\Scripts\python tools/extractor/build_upstream.py --out releases/umt-new
.venv\Scripts\python tools/animation/build_portable.py --ffmpeg releases/ffmpeg-new/ffmpeg-minimal --out releases/backend-new
.venv\Scripts\python tools/extractor/build.py --library releases/umt-new/UndertaleModLib --out releases/extractor-new
.venv\Scripts\python tools/desktop/build_trial.py --backend releases/backend-new/UTdrSpriteBackend --extractor releases/extractor-new/SpriteExtractor --out releases/windows-new
```

请把 `--msys2` 和 `--vcvars` 改为自己的安装路径；也可将便携 MSYS2 放在 `vendor` 内。FFmpeg 只启用原始帧与 qtrle MOV 编解码，不链接外部编解码库。

入口为 `releases/windows-new/SpriteLibrary.exe`，首次启动创建空 `data/`。UMT／Underanalyzer 从固定源码编译，再与当前 `tools/export.csx` 组合；裁剪配置见 `tools/extractor/TrimmerRoots.xml`。省略 `--extractor` 可构建仅浏览／导出已有 ZIP 的版本，从游戏导入时另选外部 UMT。

默认保留简繁中及英美英语的 Electron 资源，`--all-locales` 可保留全部语言；后端不打包未使用的 AVIF 插件。

## 本地候选包

```powershell
.venv\Scripts\python tools/release/package_public.py --runtime releases/windows-new --out releases/public-candidate-new
```

打包目录必须未经启动、不含 `data/`；在单独副本中试用。输出为 Windows ZIP、本项目源码 ZIP 和上游来源 ZIP，不自动上传。原生组件来源与重建说明见 [NATIVE_SOURCES.md](NATIVE_SOURCES.md)。
