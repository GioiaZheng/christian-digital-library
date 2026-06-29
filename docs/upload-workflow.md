# 上传申请流程

网站的上传入口只用于提交待审核资料，不会自动公开书目，也不会自动开放下载。

## 页面字段

- 书名
- 作者
- 文件

## Worker 行为

上传 Worker 接收表单后写入 R2：

```text
pending/uploads/{requestId}/{filename}
pending/metadata/{requestId}.json
```

metadata 记录：

- 书名
- 作者
- 文件名
- 文件大小
- 提交时间
- 状态：`pending`

## 审核边界

- 上传后不进入 `data/books.csv`。
- 上传后不生成公开详情页。
- 上传后不生成下载链接。
- 管理员审核后，再决定是否整理进入公开书目。

## 部署上传 Worker

1. 复制配置示例：

```powershell
Copy-Item workers\wrangler.upload.example.toml workers\wrangler.upload.toml
```

2. 部署：

```powershell
cd workers
wrangler deploy --config wrangler.upload.toml
```

3. 设置上传码。上传码使用 Worker Secret，不写入仓库：

```powershell
wrangler secret put UPLOAD_CODE --config wrangler.upload.toml
```

4. 将 Worker 地址写入 `public/assets/upload-config.js`：

```js
window.CDL_UPLOAD_ENDPOINT = "https://christian-digital-library-upload.<your-subdomain>.workers.dev";
```

5. 重新生成网站并提交。

## 注意

当前上传入口适合先做小规模提交。大型文件、断点续传、用户登录和后台审核界面后续再做。

不要把上传码写入 `upload-config.js` 或任何公开文件。
