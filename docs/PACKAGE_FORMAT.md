# UT／DR 素材包格式 v1

Windows 版按需读取 ZIP，不解压整库。包中只有 `manifest.json`、`catalog.json` 和 `images/**/*.png`；目录条目不需要写入 ZIP。

`manifest.json`：

```json
{
  "format": "UTdrSpriteLibrary",
  "schema": 1,
  "game": "UT",
  "name": "我的 UNDERTALE 素材",
  "version": "",
  "language": "",
  "sources": [{"file": "Undertale/data.win", "sha256": "64 位小写十六进制摘要"}]
}
```

版本及语言／补丁说明由用户填写，空字符串代表未标注。`extractor` 可记录 UMT 与提取脚本摘要。来源只记录文件名及所属目录名，不把本机绝对路径写入可另存的素材包。

`catalog.json` 保留现有提取器的 schema 1 结构：`items` 按 kind/name 分组，各组有 `variants`。精灵变体具有 `id`、`name`、`chapters`、`width`、`height`、`speed`、`speed_type` 和 `frames`。UT 的章节列表为空，DR 为实际输入章节。帧中的 `image` 指向包内 PNG，`width`/`height` 为原始尺寸；缺失纹理仍记录 missing/error，不伪造图像。

变体 ID 为资源元数据与解码像素信息的 SHA-256。同一 DR 包内相同变体合并章节，不同变体保留。包 ID 是按 ZIP 成员名排序，对每项「成员名＋零字节＋成员内容 SHA-256」计算 SHA-256，忽略 ZIP 压缩参数、成员顺序和时间戳。运行时条目键为 `包ID:变体ID`。包内游戏、版本、来源或图像改变会改变包 ID；本地编辑名称、版本和语言说明只写个人设置，不改变身份或收藏；导出 ZIP 时将有效信息写入新包 manifest，重导入这个新包时会按新内容生成独立包 ID。

导入先复制到管理目录中的临时文件，检查格式、路径、重复成员、CRC、索引引用及 PNG 尺寸，再原子改名为 `包ID.zip`。路径穿越、加密条目、不支持的格式或缺少索引引用的 PNG 会拒绝入库。验证可取消。限制为 250,000 个成员、8 GiB 总解压大小、64 MiB 目录 JSON、其余单成员 16 MiB。

个人数据存于 `data/personal/settings.sqlite3`：收藏、用户预设、显示名称、版本及语言说明、上次选择、保存位置。SQLite 事务避免多个实例保存设置时覆盖其他键。收藏不跨包关联；删除后重新导入相同包可恢复原收藏。

导出按 `显示名称_包ID前缀/normal/时间_任务ID/` 分类，拖拽按同一分类的 `drag/` 下独立 `drag-*` 目录保存。`manifest.json` 记录包身份、来源、原条目、章节和参数。原图导出逐字节复制 ZIP 内 PNG；每次输出独立副本，不覆盖旧结果。删除素材包仅删除管理目录内该 ZIP，不删除原始导入文件、个人设置或导出。
