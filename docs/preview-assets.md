# 封面与预览图片接入

网站只读取公开图片地址，不直接读取原始书籍文件。

## 推荐方式

使用 Cloudflare Worker 提供图片访问入口：

```text
浏览器
  ↓
Cloudflare Worker
  ↓ 只读取 covers/ 和 previews/
R2 bucket
```

Worker 只允许这些路径：

```text
/covers/cdl-000001.jpg
/previews/cdl-000001/page-1.jpg
/previews/cdl-000001/page-2.jpg
```

其他路径返回 `404`。

## 不建议的方式

不要直接给包含原始文件的 R2 bucket 开公开访问。这个 bucket 里同时有原始压缩包和图片资产，公开整个 bucket 会扩大暴露面。

## 部署 Worker

1. 复制配置示例：

```powershell
Copy-Item workers\wrangler.example.toml workers\wrangler.toml
```

2. 按需要调整 Worker 名称。

3. 部署：

```powershell
cd workers
wrangler deploy
```

4. 部署后得到 Worker 地址，例如：

```text
https://christian-digital-library-assets.<your-subdomain>.workers.dev
```

5. 将该地址写入本机私有 `.env`：

```text
R2_PUBLIC_BASE_URL=https://christian-digital-library-assets.<your-subdomain>.workers.dev
```

6. 重新生成资产清单，再导入公开书目。

## 公开书目字段

- `cover_image_url`：封面图地址。
- `preview_base_url`：预览图片目录地址。
- `preview_page_count`：可公开预览页数。

示例：

```csv
id,cover_image_url,preview_base_url,preview_page_count
cdl-000001,https://example.workers.dev/covers/cdl-000001.jpg,https://example.workers.dev/previews/cdl-000001,5
```
