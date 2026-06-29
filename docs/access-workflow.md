# 密码访问流程

书目详情页只提交书目编号和访问码，不保存原始文件地址。

## 流程

```text
详情页
  ↓ 输入访问码
Cloudflare Worker
  ↓ 验证 ACCESS_CODE
R2 metadata/access-map.json
  ↓ 查找书目对应文件
R2 原始文件区
  ↓
浏览器下载
```

## 生成访问映射

访问映射由本地私有 mapping 生成，不提交到公开仓库。

```powershell
python scripts\build_access_map.py --mapping C:\path\to\public_catalog_mapping.csv --output C:\path\to\access-map.json
```

生成后上传到 R2：

```text
metadata/access-map.json
```

## 部署 Worker

```powershell
wrangler deploy --config workers\wrangler.access.example.toml
```

访问码使用 Worker Secret：

```powershell
wrangler secret put ACCESS_CODE --config workers\wrangler.access.example.toml
```

部署后，将 Worker 地址写入：

```text
public/assets/access-config.js
```

## 注意

- 不要把访问码写入公开文件。
- 不要把 R2 原始文件路径写入公开网页。
- 当前入口是内部访问码方案，不是完整用户权限系统。
