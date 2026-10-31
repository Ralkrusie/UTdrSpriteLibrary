# Windows 构建

在仓库根目录操作。构建目标为 Windows x64；依赖必须明确获取，不引用本项目历史发布包。所有输出目录使用新名称。

## 环境与依赖

- Python 3.12.10；Python 依赖版本固定在 `requirements-build.txt`。
- .NET SDK 10.0.302，目标运行时 10.0.10；首次构建需联网，NuGet 缓存位于 `vendor/nuget`。
- Visual Studio C++ x64 构建工具（本次 MSVC 19.51.36252）和 MSYS2＋GNU Make，用于编译精简 FFmpeg；MSYS2 内执行 `pacman -S make`。
- [Electron 45.1.0](https://github.com/electron/electron/releases/tag/v45.1.0)：将 `electron-v45.1.0-win32-x64.zip` 保存为 `vendor/electron/electron-verified.zip`，官方 `SHASUMS256.txt` 放在同目录。
- [UTMT 0.9.2.0](https://github.com/UnderminersTeam/UndertaleModTool/releases/tag/0.9.2.0)：将 `UTMT_CLI_v0.9.2.0-Windows.zip` 保存为 `vendor/umt/cli-download.zip`，解压到 `vendor/umt/0.9.2.0`，其中直接包含 `UndertaleModLib.dll`。ZIP 的 SHA-256 必须为 `e7573e45d107be34f81f955c6e4afc3c7c8f2628e5a6f307a871e3825b3dfb40`。

构建脚本校验上述归档；UI 资源位于 `assets/ui`。将配套来源包中的 `upstream-sources` 内容放入 `vendor/release-sources`，或使用下方收集命令获取。

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

入口为 `releases/windows-new/SpriteLibrary.exe`，首次启动创建空 `data/`。UTMT／Underanalyzer 从固定源码编译，再与当前 `tools/export.csx` 组合；裁剪配置见 `tools/extractor/TrimmerRoots.xml`。省略 `--extractor` 可构建仅浏览／导出已有 ZIP 的版本，从游戏导入时另选外部 UTMT。

默认保留简繁中及英美英语的 Electron 资源，`--all-locales` 可保留全部语言；后端不打包未使用的 AVIF 插件。

后端构建同时生成静默入口 `UTdrSpriteBackend.exe` 与控制台入口 `utdr.exe`，共用 `_internal` 依赖。Windows 桌面目录提供 `utdr.cmd`；POSIX 提供 `utdr` 启动脚本（macOS 位于 `.app/Contents/Resources`）。使用方式见 [CLI.md](CLI.md)。

CLI 集成检查（所有测试数据与导出写入 `releases/` 独立目录）：

```powershell
.venv\Scripts\python tools/animation/test_cli.py
.venv\Scripts\python tools/animation/test_cli.py --cli releases/backend-new/UTdrSpriteBackend/utdr.exe
```

## 本地候选包

```powershell
.venv\Scripts\python tools/release/package_public.py --runtime releases/windows-new --out releases/public-candidate-new
```

打包目录必须未经启动、不含 `data/`；在单独副本中试用。输出为 Windows ZIP、本项目源码 ZIP 和上游来源 ZIP，不自动上传。原生组件来源与重建说明见 [NATIVE_SOURCES.md](NATIVE_SOURCES.md)。


## macOS／Linux 原生候选构建

以下入口由对应平台的 CI 构建和自动检查；macOS／Linux 版本未在对应机器上人工实测。首版只导入现有 ZIP 素材包，不内置游戏提取器；支持范围须以实际构建及运行结果为准。需在目标系统和目标 CPU 架构上构建，不能从 Windows 交叉冻结 Python 后端。

准备 Python 3.12.10、Clang／GCC、Make、unzip；macOS 还需 Xcode Command Line Tools。Linux 当前构建基线为 Ubuntu 22.04 x64，桌面运行需要 GTK3、NSS、ALSA、GBM 等 Electron 系统库。不要通过关闭 Electron 沙箱规避系统兼容问题。

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-build.txt
mkdir -p vendor/release-sources releases
curl --fail --location --retry 3 https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n7.1.zip -o vendor/release-sources/FFmpeg-n7.1.zip
python tools/ffmpeg/build_posix.py --out releases/ffmpeg-native
python tools/animation/build_portable.py --ffmpeg releases/ffmpeg-native/ffmpeg-minimal --out releases/backend-native
python tools/desktop/fetch_electron.py
python tools/desktop/build_posix.py --backend releases/backend-native/UTdrSpriteBackend --out releases/desktop-native
```

FFmpeg 和 Electron 下载均核对固定来源摘要。输出 macOS `.app` ZIP 或 Linux `.tar.gz`；保留可执行权限与符号链接。macOS 目前使用开发用 ad-hoc 签名，未做 Developer ID 签名、公证，不代表普通用户可直接安装的正式分发包。

macOS 数据位于 `~/Library/Application Support/UTdrSpriteLibrary`；Linux 位于 `${XDG_CONFIG_HOME:-~/.config}/UTdrSpriteLibrary`。可通过绝对路径环境变量 `UTDR_DATA_DIR` 指定独立数据目录，包括测试目录。Windows 默认仍使用程序目录下的 `data/`。

仓库的 `macOS and Linux candidates` 工作流仅支持手动触发，分别准备 macOS arm64、macOS x64、Linux x64。它包含后端导出与桌面启动检查，通过后保存候选包为 Actions 附件，不创建 GitHub Release。实际外部软件接收拖拽、Linux 桌面会话差异和 macOS 下载后启动仍需实机确认。


## 手机 PWA 试用版

```powershell
.venv\Scripts\python tools/mobile/build.py --out releases/mobile-pwa-new
.venv\Scripts\python -m http.server 8765 --bind 127.0.0.1 --directory releases/mobile-pwa-new
```

电脑访问 `http://localhost:8765`。手机安装需要将生成目录部署到 HTTPS 静态站点（可用 GitHub Pages，支持仓库子路径）；直接双击 HTML 或用局域网 HTTP 地址不能完整启用离线功能。构建不上传，不包含素材包，也不依赖 Python 服务处理素材。`build_offline.py` 现为同一 PWA 构建入口，不再生成旧单文件 HTML／旧格式素材包。

Safari 分享菜单 → 添加到主屏幕；安卓浏览器菜单 → 安装应用／添加到主屏幕。首次联网加载到“离线资源已就绪”后可离线使用。更新在旧页面全部关闭后启用，素材和设置保留。包、收藏及参数存于当前站点的 IndexedDB，清除网站数据或系统回收存储可能导致丢失，请保留原始 ZIP。

导入桌面版 v1 ZIP，按需解压帧，支持存储与 Deflate 压缩；需要支持 `DecompressionStream('deflate-raw')` 的现代浏览器。首版限制 ZIP 512 MiB、总解压 1 GiB，不支持 ZIP64。导入校验 CRC、索引、路径和 PNG 头尺寸；包身份沿用桌面内容摘要。支持多包切换／移除、搜索、章节／多帧／同名／收藏筛选、卡片大小、帧预览、独立批量／详情参数记忆和收藏。手机版不提供图片复制；系统分享仅在浏览器支持该文件时显示，亦可保存文件。卡片与详情预览自动适应区域，导出倍率独立设置。

缩放 0.25–20×、速度 0.1–120 FPS；单批最多 50 个精灵、1600 万输出像素，单边不超过 8192，超限要求降低倍率或缩小批次。多文件导出合为 ZIP。首版无游戏提取、复杂包管理、桌面预设、MOV 或拖拽。iOS／Android 安装、存储回收及目标软件粘贴／分享体验尚未真机验证。

开发验证：运行 `tools/mobile/test_fixture.py` 生成原创微型素材，再用已安装的 Playwright 执行 `node tools/mobile/test_pwa.cjs releases/mobile-pwa-new`。Windows 默认使用 Edge，其他环境可设置 `PWA_BROWSER` 为浏览器可执行路径。测试只使用独立浏览器上下文，产物写入 `releases/mobile-pwa-test`。


## Android APK

`tools/mobile/android` 使用安卓系统 WebView 加载 APK 内全部页面资源，无网络权限、无服务器和游戏提取依赖。Android 9 及以上，并需要支持 Deflate 解压的较新 Android System WebView。首次安装也可离线；ZIP 素材另行导入。原生文件选择、保存和分享已实现；图片复制已移除。此前版本已由用户试用；本次原生交互调整仍需真机确认。

Windows 构建准备 JDK（本机用 25.0.3），将 Google 官方仓库 `https://dl.google.com/android/repository/` 中的 `platform-35_r02.zip` 和 `build-tools_r35_windows.zip` 放到 `vendor/android/`。脚本核对 SDK 清单中的固定 SHA-1，从当前源码生成 APK，不需要 Gradle、npm 或旧发布包。

```powershell
.venv\Scripts\python tools/mobile/android/build.py --jdk D:/Development/Java/jdk-25.0.3 --out releases/android-new
```

仅将输出中的 `UTdrSpriteLibrary-0.3.0-android.apk` 发给测试者，其余目录是本地构建依赖。安装时允许当前文件管理器／聊天软件安装此来源的应用。素材、收藏、设置保存在应用私有空间，卸载或清除数据会删除；保存到系统文件的位置由用户选择。分享副本保留在应用私有 exports 目录，避免临时 URI 失效。

公开 APK 延续此前安装包的签名，以支持覆盖升级。维护者须备份 `vendor/android/offline-test.jks`，并持续使用同一密钥；密钥不进入源码或发布附件。构建只生成本地产物。
