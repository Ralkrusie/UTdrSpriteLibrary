# UTdrSpriteLibrary

UT／DR 精灵素材管理与导出。

An unofficial local tool for browsing, organizing and exporting UNDERTALE and DELTARUNE sprites.

## 下载与使用

[下载最新版本](https://github.com/Ralkrusie/UTdrSpriteLibrary/releases/latest)，打开应用右上角的「使用说明」了解操作。

| 平台 | 启动方式与功能 |
| --- | --- |
| Windows x64 | 解压 ZIP，运行 `SpriteLibrary.exe`。支持从游戏制作素材包、浏览、收藏、预览、批量导出和拖拽。 |
| macOS Apple Silicon／Intel | 解压对应 ZIP，打开 `.app`。支持导入 ZIP 素材包和桌面导出功能。 |
| Linux x64 | 解压 tar.gz，运行 `SpriteLibrary`。支持导入 ZIP 素材包和桌面导出功能。 |
| Android 9+ | 安装 APK，导入 ZIP 素材包；支持浏览、收藏、预览、PNG／GIF／APNG 保存和分享。需较新的 Android System WebView。 |

macOS／Linux 已通过原生构建和自动检查，尚未人工实机验证；macOS 尚未公证。安卓版此前已由用户试用，本次更新的浏览器跳转等原生交互仍待真机确认。

桌面导出支持 PNG、GIF、APNG、透明 MOV；Windows 只读游戏数据。素材包独立导入，游戏素材版权归原权利人。

Windows 数据位于程序旁的 `data`，macOS／Linux 位于系统用户数据目录。升级 Windows 时保留原 `data`；安卓覆盖安装保留应用数据，卸载或清除数据会移除本机素材与设置。请保留原始素材包 ZIP。

## 命令行与开发

桌面版提供 `utdr` 命令行（Windows 为 `utdr.cmd`）：

```sh
utdr --help
utdr packages list --json
utdr schema --json
```

[CLI 与 AI 调用](docs/CLI.md) · [构建说明](docs/BUILD.md) · [功能约定](docs/REQUIREMENTS.md) · [素材包格式](docs/PACKAGE_FORMAT.md)

## 相关链接

- [UTdr 原版素材包](https://wwaya.lanzouv.com/b01euw4aoh) · 密码：`jarona`
- [联系作者（b站）](https://space.bilibili.com/571877935)
- [支持作者（爱发电）](https://afdian.com/a/ralkrusie)

## 许可

原创代码采用 [GPL-3.0-or-later](LICENSE)。[第三方软件](THIRD_PARTY_NOTICES.md)保留各自许可；[游戏衍生界面资源](ASSET_NOTICE.md)及导出的游戏素材不在代码授权范围内。

非官方项目，与 Toby Fox、Fangamer 无隶属或背书关系。
