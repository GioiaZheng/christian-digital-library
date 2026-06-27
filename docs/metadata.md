# 公开元数据规范

`data/books.csv` 只保存可以公开展示的书目信息。

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `id` | 是 | 稳定唯一的小写标识。 |
| `clean_title` | 是 | 已核实的展示书名。 |
| `author` | 否 | 作者。 |
| `publisher` | 否 | 出版机构。 |
| `year` | 否 | 四位出版年份。 |
| `language` | 否 | 主要语言。 |
| `category` | 是 | 已定义的分类标识。 |
| `tags` | 否 | 使用分号分隔的公开标签。 |
| `description` | 否 | 经审核的公开简介。 |
| `table_of_contents` | 否 | 使用竖线分隔的公开目录项。 |
| `copyright_status` | 是 | 已核实的版权状态。 |
| `can_public_download` | 是 | 只接受 `true` 或 `false`。 |

## 规则

- 未核实的记录不进入公开 CSV。
- 没有可靠依据时留空，不猜测作者、出版社或年份。
- 简介和目录写入前也要确认可以公开使用。
- `can_public_download` 默认为 `false`。
