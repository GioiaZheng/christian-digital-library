# 上传申请流程

网站的上传入口只用于提交待审核资料，不会自动公开书目，也不会自动开放下载。

## 页面字段

- 书名
- 作者
- 译者（可选）
- 文件

## Worker 行为

上传 Worker 接收表单后写入 R2：

公开上传表单不需要提交码。所有上传只进入待审核区，不会自动进入公开书目。

```text
pending/uploads/{requestId}/{filename}
pending/metadata/{requestId}.json
```

metadata 记录：

- 书名
- 作者
- 译者（如有）
- 文件名
- 文件大小
- 提交时间
- 状态：`pending`

## 审核边界

- 上传后不进入 `data/books.csv`。
- 上传后不生成公开详情页。
- 上传后不生成下载链接。
- 管理员审核后，再决定是否整理进入公开书目。

## 本地审核脚本

管理员可以在本机使用脚本查看待审核记录。脚本只读取本地环境变量或本地 `.env`，不会把密钥写入仓库。

列出待审核上传：

```powershell
python scripts\review_uploads.py --env-file C:\path\to\.env list
```

查看某条记录：

```powershell
python scripts\review_uploads.py --env-file C:\path\to\.env show <提交 ID>
```

删除测试或无效提交：

```powershell
python scripts\review_uploads.py --env-file C:\path\to\.env delete <提交 ID> --yes
```

当前脚本只处理 `pending/` 区。正式入库仍需要人工核对书名、作者、译者、版本、版权状态和分类后，再整理到书目数据中。

## 部署上传和管理员 Worker

1. 复制配置示例：

```powershell
Copy-Item workers\wrangler.upload.example.toml workers\wrangler.upload.toml
```

2. 部署：

```powershell
cd workers
wrangler deploy --config wrangler.upload.toml
```

3. 设置管理员密码。管理员密码使用 Worker Secret，不写入仓库，也不要与阅读访问码相同：

```powershell
wrangler secret put ADMIN_CODE --config wrangler.upload.toml
```

4. 将 Worker 地址写入 `public/assets/upload-config.js`：

```js
window.CDL_UPLOAD_ENDPOINT = "https://christian-digital-library-upload.<your-subdomain>.workers.dev";
```

5. 重新生成网站并提交。

## 注意

当前上传入口适合先做小规模提交。大型文件、断点续传和正式用户登录后续再做。

不要把管理员密码、阅读访问码或任何 Secret 写入 `upload-config.js` 或任何公开文件。
