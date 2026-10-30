# Build from source / 从源码构建

当前桌面目标为 Windows x64。使用 Python 3.12.10、.NET SDK 10.0.302（目标运行时 10.0.10）、Electron 45.1.0。其他系统的桌面版尚未完成构建与验证。所有构建输出必须使用新的目录名；不要覆盖已有用户数据。

## 固定依赖

1. 用 Python 3.12 创建 `.venv`，执行 `python -m pip install -r requirements-build.txt`。依赖版本固定在 requirements 文件中，包括 Pillow 12.3.0、imageio-ffmpeg 0.7.0、PyInstaller 6.16.0。
2. 从 [Electron v45.1.0](https://github.com/electron/electron/releases/tag/v45.1.0) 获取 `electron-v45.1.0-win32-x64.zip` 和 `SHASUMS256.txt`。分别保存为 `vendor/electron/electron-verified.zip` 和 `vendor/electron/SHASUMS256.txt`。组装脚本校验 ZIP 摘要。
3. 从 [UndertaleModTool 0.9.2.0](https://github.com/UnderminersTeam/UndertaleModTool/releases/tag/0.9.2.0) 获取 `UTMT_CLI_v0.9.2.0-Windows.zip`，保存为 `vendor/umt/cli-download.zip`。SHA-256 必须为 `e7573e45d107be34f81f955c6e4afc3c7c8f2628e5a6f307a871e3825b3dfb40`，解压到 `vendor/umt/0.9.2.0`，其中直接包含 UndertaleModLib.dll。不要使用历史本项目发布包作为依赖。
4. 安装上述 .NET SDK。`tools/extractor/build.py` 将从当前 `tools/export.csx` 生成只读入口，用 `SpriteExtractor.csproj` 和 `TrimmerRoots.xml` 编译并裁剪。NuGet 使用 `vendor/nuget` 缓存，首次运行需要网络。
5. 两项 UI 图像已在 `assets/ui`；其来源与许可例外见根目录 `ASSET_NOTICE.md`。不需要完整字体或游戏包。

## 构建命令

在仓库根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python tools/animation/build_portable.py --out releases/backend-new
.venv\Scripts\python tools/extractor/build.py --out releases/extractor-new
.venv\Scripts\python tools/desktop/build_trial.py --backend releases/backend-new/UTdrSpriteBackend --extractor releases/extractor-new/SpriteExtractor --out releases/windows-new
```

运行 `releases/windows-new/SpriteLibrary.exe`。首次启动自动创建空的 data 目录；构建不带入开发者素材包和设置。只浏览／导出既有素材包时可不传 `--extractor`；此时从游戏制作素材包需要用户指定外部 UMT CLI。

## 验证与公开候选包

```powershell
node tools/desktop/test_boundary.cjs
node tools/desktop/test_drag.cjs
.venv\Scripts\python tools/animation/verify_portable.py --backend releases/backend-new/UTdrSpriteBackend
.venv\Scripts\python tools/release/collect_sources.py
.venv\Scripts\python tools/release/package_public.py --runtime releases/windows-new --out releases/public-candidate-new
```

打包脚本拒绝含 data/ 的运行目录。应在单独测试副本上启动软件，保留原始构建目录供打包。打包输出包括本项目源码、Windows 候选 ZIP、已收集上游源码和 SHA-256 清单；不会提交、推送或上传。

`collect_sources.py` 下载固定提交／版本并记录摘要。UMT 对应提交为 `03c7048438347799e0717b6e57a9358d000472e0`；其 Underanalyzer 子模块为 `4ff50a866b4c1a7acee8cebe6a56d6a48709b453`。如自行构建 UMT，需将两者还原至对应目录并按上游说明构建。

**这些步骤可以重建本项目代码，但当前不构成随附所有原生依赖的完整可重现构建。** FFmpeg 静态库、Magick.Native 依赖及 UMT 二进制对应源码的核查尚未全部完成；具体状态见 `RELEASE_PREPARATION.md`。不要把收集若干主项目源码归档描述为已经完成全部对应源码义务。

测试使用生成的小型素材包，输出写入 releases 下独立目录。真实游戏导入始终只读；不向游戏目录保存。当前没有 macOS／Linux 的正式桌面产物。
