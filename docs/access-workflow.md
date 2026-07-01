# 访问码与在线阅读流程

书目详情页只提交书目编号和访问码，不保存访问码，也不暴露原始文件地址。

## 下载流程

```text
详情页
  ↓ 输入访问码
Cloudflare Worker
  ↓ 验证 ACCESS_CODE
R2 访问映射
  ↓ 找到对应原始文件
浏览器下载
```

## 在线阅读流程

在线阅读不再下载 ZIP，也不在浏览器里解压 ZIP。

```text
详情页
  ↓ 输入访问码
Cloudflare Worker
  ↓ 返回短时阅读 token
reader.html
  ↓ 按需请求页面图片
Cloudflare Worker
  ↓ 校验 token
R2 阅读页图片
```

阅读页文件按书目编号放在 R2 的阅读区：

```text
reader/{book_id}/manifest.json
reader/{book_id}/page-0001.webp
reader/{book_id}/page-0002.webp
```

`manifest.json` 至少包含：

```json
{
  "title": "书名",
  "page_count": 120,
  "page_extension": "webp"
}
```

没有生成阅读页图片的书，在线阅读会提示“阅读版正在生成”，下载入口仍然可用。

## 部署

```powershell
wrangler deploy --config workers\wrangler.access.example.toml
```

访问码使用 Worker Secret：

```powershell
wrangler secret put ACCESS_CODE --config workers\wrangler.access.example.toml
```

可选：单独设置阅读 token 密钥。

```powershell
wrangler secret put READER_TOKEN_SECRET --config workers\wrangler.access.example.toml
```

## 注意

- 不要把访问码写入公开文件。
- 不要把 R2 原始文件路径写入公开网页。
- 旧 ZIP 只作为历史导入源和临时备份，不再作为新增书籍的正式存储格式。
- 正式下载目标应是解包、核对后的 PDF、EPUB 或 MOBI；在线阅读使用预先生成的阅读页图片。
