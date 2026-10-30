# Public release preparation / 公开发布准备

Status: source-only repository publication. The Windows candidate remains local; corresponding-source verification for the bundled binary is NOT complete.
状态：本轮仅公开源码。Windows 候选包保留在本地；随附二进制的完整对应源码核对尚未完成。

## Completed design

- Original project code: GPL-3.0-or-later. Third-party code keeps its license. UI artwork exceptions are explicit in ASSET_NOTICE.md.
- Public package starts empty. No data/, library/, game ZIP, game archive, personal settings, exports, developer environment or cache is included.
- Only the agreed heart and fixed title artwork are included. The title no longer contains an embedded atlas. Their unverified redistribution authorization is an accepted maintainer decision, not a claim of permission.
- Electron retained; Windows x64 is the tested artifact. macOS/Linux are not claimed as release-ready.

## Remaining binary-distribution requirements

1. The bundled gyan.dev FFmpeg 7.1 executable enables GPL/version3 and many static external libraries (see the recorded -version output). The FFmpeg n7.1 archive alone does not provide those libraries' exact source versions, patches and build scripts. Obtain the complete matching build-source set, or replace it with a reproducibly built encoder whose complete source and build recipe can accompany the release. This has not been waived by the UI-artwork decision.
2. Check Magick.Native's native/delegate notices and matching source requirements against the actual included DLL; an upstream Magick.NET source archive is not by itself a complete audit of the native build.
3. The UMT source and pinned Underanalyzer submodule are collected. Before binary distribution, verify that the release binaries correspond to those snapshots and that the included build/trimming instructions plus dependencies constitute the required corresponding source.

No license files, homepage links or this checklist should be described as a complete legal certification. Do not advertise the candidate as cleared for binary redistribution until these items are closed. Source-code publication can be reviewed separately; copyrighted UI assets are expressly outside the code-license grant.

## Local packaging

`python tools/release/package_public.py --runtime <fresh-current-build> --out <new-directory>`

Creates a source snapshot, a clean Windows candidate, available upstream-source archives, notices and SHA256SUMS. It refuses a runtime containing data/ and does not commit, push, upload or create a GitHub release. Supply an untouched fresh build after verifying a separate test copy. The source archive excludes local status/history documents containing machine-specific paths.

## Repository description

中文：用于浏览、预览、管理和导出 UNDERTALE／DELTARUNE 精灵素材的非官方本地工具。
English: An unofficial local tool for browsing, previewing, organizing and exporting UNDERTALE and DELTARUNE sprites.
