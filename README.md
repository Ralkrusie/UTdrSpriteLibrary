# UTdrSpriteLibrary

UT／DR 精灵素材管理与导出。

An unofficial local tool for browsing, previewing, organizing and exporting UNDERTALE and DELTARUNE sprites.

支持素材包切换、搜索与收藏、动画预览、批量导出，以及 Windows 原生文件拖拽。导出格式包括 PNG、GIF、APNG 和透明 MOV。

Windows x64 测试版见 [GitHub Releases](https://github.com/Ralkrusie/UTdrSpriteLibrary/releases)。macOS／Linux 桌面适配未完成，移动端为原型。工具只读游戏数据，不附带素材包，需自行导入 ZIP 或从自己的游戏目录提取。

## 快速开始

Windows 用户下载 `windows-x64.zip`，完整解压到可写目录，双击 `SpriteLibrary.exe`；无需安装 Python 或 FFmpeg。另两个源码包供开发者使用，普通使用无需下载。

从源码运行浏览器版（Windows、Python 3.12），在仓库根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-animation.txt
.venv\Scripts\python tools/animation/server.py --open --auto-port
```

在“管理素材包”中导入 ZIP；从游戏制作素材包需另行准备专用提取器或 UMT CLI，见[构建说明](docs/BUILD.md)。浏览器版填写本地路径；桌面版提供原生文件选择和拖拽。

服务仅监听本机，默认数据目录为 `data/`，可用 `--data` 指定其他位置：

- `packages/`：素材包。
- `personal/`：收藏、预设和个人设置。
- `exports/`：默认导出位置，按素材包分组，`normal/` 为手动导出，`drag/` 为拖拽结果。

删除素材包不会删除个人设置或导出结果。MOV 保存一轮动画，接收软件的透明与循环支持需实际确认。

## 文档

[构建说明](docs/BUILD.md) · [功能约定](docs/REQUIREMENTS.md) · [素材包格式](docs/PACKAGE_FORMAT.md)

## 许可

原创代码采用 [GPL-3.0-or-later](LICENSE)。[第三方软件](THIRD_PARTY_NOTICES.md)保留各自许可；[游戏衍生界面资源](ASSET_NOTICE.md)及导出的游戏素材不在代码授权范围内。

非官方项目，与 Toby Fox、Fangamer 无隶属或背书关系。
