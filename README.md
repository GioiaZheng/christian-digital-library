# 基督教数字图书馆

面向中文读者的基督教书目检索与浏览项目。

本仓库包含静态网站、公开书目数据、页面生成脚本、测试和必要的项目文档。图书文件与公开网站分开管理，网站默认不提供下载链接。

## 当前功能

- 中文首页与书目目录
- 按书名、作者、分类和标签搜索
- 分类浏览与书目详情页
- CSV 驱动的静态页面生成
- GitHub Pages 自动部署
- 数据和仓库文件检查

## 目录结构

```text
data/       公开书目与分类
docs/       项目文档
public/     样式和浏览器脚本
scripts/    检查与页面生成脚本
site/       生成后的静态网站
src/        页面模板
tests/      自动化测试
```

## 本地运行

需要 Python 3.11 或更高版本，无第三方依赖。

```bash
python scripts/check_repository.py
python -m unittest discover -s tests -v
python scripts/generate_catalog.py
python -m http.server 8000 --directory site
```

打开 `http://localhost:8000`。

## 公开书目

公开数据位于 `data/books.csv`。目录由馆藏清单生成，不确定的作者、版本和出版信息保持为空。

字段说明见 [元数据规范](docs/metadata.md)。

## 内容原则

- 只发布适合公开展示的书目信息。
- 不在 Git 仓库中保存大型图书文件。
- 不提交密钥、内部记录或私有文件地址。
- 版权状态不明确时不提供公开下载。

## 部署

`main` 分支更新后，GitHub Actions 会运行检查、生成网站并部署到 GitHub Pages。
