# UTdrSpriteLibrary

UT／DR 精灵素材管理与导出：ZIP 素材包、多版本切换、收藏、搜索、动画预览、导出与 Windows 原生拖拽。

An unofficial local tool for browsing, previewing, organizing and exporting UNDERTALE and DELTARUNE sprites.

非官方项目，与 Toby Fox、Fangamer 无隶属或背书关系。工具只读游戏数据，不修改游戏包；不附带完整游戏素材包。需要自行导入素材包或从自己的游戏目录提取。

已确认目标见 [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)，构建与验证范围见 [docs/BUILD.md](docs/BUILD.md)。Windows 桌面优先；macOS／Linux 尚未完成桌面适配，移动端保留原型。当前为本地候选版本，二进制正式分发前的待办见 [RELEASE_PREPARATION.md](RELEASE_PREPARATION.md)。

## 源码运行

Windows Python 3.12：
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python tools/animation/server.py --open --auto-port
```

服务只监听本机。默认数据目录为项目下 data；可用 `--data` 指定独立位置。浏览器版直接填写文件路径；Windows 桌面版提供原生文件／文件夹选择。

在“管理素材包”中导入 ZIP，或选择游戏目录制作素材包。旧项目复制过来的 library 可用“迁移本地旧素材”入口制作 ZIP；原目录保持不变。素材包格式见 [docs/PACKAGE_FORMAT.md](docs/PACKAGE_FORMAT.md)。

- data/packages：只读 ZIP 素材包。
- data/personal：SQLite 个人设置，包含收藏、用户预设、库名称、卡片大小和保存路径。
- data/exports：默认结果导出，按素材包分类，内部用 normal／drag 区分手动与拖拽结果；可改到其他目录。
- 桌面预览与导入中间文件位于本实例临时目录，正常退出时清理。

UT 导入读取所选目录下 data.win；DR 导入读取实际存在的 chapterN_windows/data.win，不要求章节连续。导入调用随附专用提取器或明确指定的 UMT CLI，只读加载游戏，前后核对源文件摘要。版本未知时允许留空，不自动猜测。

素材浏览右上方可调整卡片大小（180–360 px），自动记住设置；此项不影响导出尺寸。批量导出与详情页的“自定义缩放”支持 0.25–20× 小数倍率。勾选“使用预设”后仅可切换已有预设，取消勾选后可编辑或删除。

## Windows 构建

Electron ZIP 放到 vendor/electron/electron-verified.zip，同目录 SHASUMS256.txt 用于校验。固定依赖、官方获取地址与步骤见 [docs/BUILD.md](docs/BUILD.md)。

标题与红心位于 assets/ui，构建校验摘要。标题仅包含固定文字的可见像素，不包含完整字体图集。来源及源码许可例外见 [ASSET_NOTICE.md](ASSET_NOTICE.md)。构建无需完整游戏素材包。

```powershell
.venv\Scripts\python tools/animation/build_portable.py --out releases/backend-new
.venv\Scripts\python tools/extractor/build.py --out releases/extractor-new
.venv\Scripts\python tools/desktop/build_trial.py --backend releases/backend-new/UTdrSpriteBackend --extractor releases/extractor-new/SpriteExtractor --out releases/desktop-new
```

Windows 精简构建保留简繁中、英美英语的 Electron 语言资源；传入 `--all-locales` 可打包全部语言。后端不打包本工具未使用的 AVIF 插件，保留 PNG/GIF/APNG/MOV 所需组件。继续采用 Electron 跨平台路线；当前构建和验证仍限 Windows。

输出目录必须不存在。专用提取器构建需 .NET 10 SDK、校验后的 vendor/umt/cli-download.zip 及其解压目录；从当前 export.csx 编译，裁掉交互式 CLI、脚本编译器与未使用程序集，约 48.5 MiB。普通用户无需安装 .NET。仍可改用 `--umt vendor/umt/0.9.2.0` 随附完整 CLI 运行目录，或手动指定外部 CLI。运行和导出已有 ZIP 包不需要提取器。

桌面入口为 SpriteLibrary.exe，后端 UTdrSpriteBackend.exe 为无控制台程序。Python、Pillow、FFmpeg 随后端构建复制，普通用户无需安装。构建不复制 library、旧发布包、用户设置或完整素材包；仅包含声明的红心与固定标题 UI 图像。

## 检查

```powershell
node tools/desktop/test_boundary.cjs
node tools/desktop/test_drag.cjs
.venv\Scripts\python tools/animation/test_encoder.py
.venv\Scripts\python tools/animation/test_export_files.py
.venv\Scripts\python tools/animation/test_mov.py
.venv\Scripts\python tools/animation/test_library.py
.venv\Scripts\python tools/animation/test_lifecycle.py
.venv\Scripts\python tools/animation/verify_portable.py --backend releases/backend-new/UTdrSpriteBackend
```

集成与桌面拖拽测试输出位于 releases 下独立测试目录。打包测试会清除后端 PATH 中的 Python/FFmpeg，确认使用内置依赖。MOV 使用 qtrle/ARGB，保存一轮动画；目标剪辑软件的接收及循环行为需实际验证。

## 源码布局

- tools/animation：本地服务、素材包、个人设置、游戏导入、浏览界面、编码与后端构建。
- tools/desktop：Electron 外壳、原生拖拽、Windows 打包及检查。
- tools/mobile：保留的静态网页及 HTML＋ZIP 离线原型。
- tools/extractor：从当前提取脚本构建专用 Windows 提取器与全量对比检查。
- tools/build.py、tools/export.csx：只读 UT／DR 提取命令行入口与 UMT 脚本。
- library、vendor、releases、data、.venv：本地素材、依赖、生成物和个人数据，不入 Git。

## 许可 / License

本项目原创代码采用 **GPL-3.0-or-later**，详见 [LICENSE](LICENSE)。第三方软件保留各自许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。游戏衍生 UI 图像和导出的游戏资源不包含在本项目的 GPL 授权范围内，见 [ASSET_NOTICE.md](ASSET_NOTICE.md)。

Original code is licensed under GPL-3.0-or-later. Third-party software retains its own licenses; game-derived UI artwork and exported game assets are excluded from this grant. See the notices above. No materials are uploaded automatically.
