# 原生组件来源与重建

Windows 测试版配套提供本项目源码 ZIP 和上游来源 ZIP。解压来源包，将 `upstream-sources/` 中的归档与 manifest.json 放入源码目录的 `vendor/release-sources/`；构建命令见 docs/BUILD.md。来源包保留完整上游归档、许可证和 SHA-256，不与应用源码混放。

## FFmpeg

- 固定源码：FFmpeg `n7.1`，归档 `FFmpeg-n7.1.zip`。
- `tools/ffmpeg/build.py` 使用 MSVC 和 MSYS2 Make，静态编译原始 RGBA／qtrle MOV 编解码，关闭网络、自动检测和外部编解码库；没有启用 GPL/nonfree 组件。构建采用 LGPL-2.1-or-later。
- 唯一生成的源码文件为 `VERSION`，内容 `7.1-utdr1`，避免误读本项目 Git 提交号。没有修改编码算法。
- Windows 包 `backend/licenses/FFmpeg-*` 保留配置、编译器与构建工具版本及源码说明。完整源码和本项目构建脚本共同提供重建依据。

## UMT／Underanalyzer

- UMT：`03c7048438347799e0717b6e57a9358d000472e0`；Underanalyzer 子模块：`4ff50a866b4c1a7acee8cebe6a56d6a48709b453`。
- `tools/extractor/build_upstream.py` 将两个归档恢复为上游目录结构并编译；唯一上游改动是把 PreBuild 中的 Git 探测替换为固定来源提交记录。此修改由脚本明确生成，提取逻辑不变。
- `tools/extractor/build.py` 再编译本项目只读提取脚本，并应用 TrimmerRoots.xml。输出 `upstream-source-build.json`、`build-profile.json` 记录对应关系。原始 UMT CLI ZIP 仅提供经过摘要校验的第三方 DLL；UMT 和 Underanalyzer DLL 使用新编译结果。

## Magick.Native 与图像依赖

- Magick.NET 14.16.0 对应 Magick.Native `1187ae6ead3c4ac8b3020cfd8a98b9990697eec6`（发布 `2026.727.1945`），ImageMagick `360eda553586e389c9c725fc49df94f209a8a3c7`。
- `tools/release/verify_native.py` 比对 UMT 内的签名 DLL 与官方 `windows-Q8-x64.zip`：排除 PE 校验和、签名目录和证书后，其余字节全部一致。完整官方许可位于 `licenses/third-party/Magick.Native-NOTICE.txt`；比对记录仅供本地构建使用。
- 来源包包含 Dependencies `2026.07.27.0556`、其 `clone-dependencies.sh` 固定的 37 项 Windows 依赖，以及官方脚本指定的 Configure `2026.05.30.2033`／`2026.07.15.0628`。保留各依赖仓库中的补丁与构建文件。
- 重建时，将各归档去除最外层目录后，按 `clone-dependencies.sh` 的名称放入 Dependencies 仓库的 `Dependencies/<名称>/`；按该仓库 `.github/workflows/main.yml` 的 Windows 配置编译依赖，再按 Magick.Native 的同名工作流编译 Q8 x64。原生源码置于 `Magick.Native/src/ImageMagick/ImageMagick`；对应 Configure 和依赖产物的获取／使用步骤见上游脚本。
- JPEG XL 的 skcms、sjpeg、测试和额外工具在依赖构建脚本中关闭；实际使用的 brotli、lcms、highway 等源码随上述依赖提供。没有另外打包测试用 Git 子模块。

本次没有重新编译 Magick.Native；采用上游构建，并保留其固定来源与完整许可。本文说明来源对应与重建方式，不承诺不同编译环境产生完全相同的二进制字节。
