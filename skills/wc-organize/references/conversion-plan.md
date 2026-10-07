# 临时转换计划

脚本依赖 Python 3 标准库。以下命令中的 `SKILL_DIR` 是本 Skill 的真实目录；先解析安装入口，不能假定当前工作目录。输入路径、计划路径与输出路径均可使用绝对路径。

```bash
python3 "$SKILL_DIR/scripts/render_corpus.py" inspect input.csv
python3 "$SKILL_DIR/scripts/render_corpus.py" inspect input.csv --text-column '视频文案（text）'
python3 "$SKILL_DIR/scripts/render_corpus.py" render input.csv --plan /tmp/conversion-plan.json --output 'input·断行整理版.md'
python3 "$SKILL_DIR/scripts/render_corpus.py" check input.csv --plan /tmp/conversion-plan.json --output 'input·断行整理版.md'
```

`inspect` 输出源文件 SHA-256、编码、列名、正文列与带源行序号的完整记录，供读取和生成计划。它不写文件。`render` 默认拒绝覆盖既有文件；明确在更新已授权的成品时追加 `--overwrite`。`check` 只读回核对。

计划是内部临时 JSON，不是交付结构。大文件可以分批整理 `records`，最后合并成一份完整计划。`row` 是 CSV 表头之后从 1 开始的记录序号，不是物理文本行号，也不是点赞排序后的名次。

```json
{
  "source_sha256": "从inspect复制的完整SHA256",
  "text_column": "视频文案（text）",
  "title_column": "标题（title）",
  "likes_column": "点赞数（digg_count）",
  "records": [
    {
      "row": 1,
      "edits": [],
      "opening": ["为什么总是找不到钥匙？"],
      "hooks": [{"text": "为什么", "mechanism": "发问"}],
      "delivery": [["回家以后，", "把它放在门边的盒子里。"]],
      "closing": ["每天都放同一个地方。"]
    }
  ]
}
```

- 三个列名必须来自 `inspect`，缺少标题或点赞字段时对应值写 `null`。不猜造列名。正文列必须存在，不能同时充当标题或点赞列。
- `records` 包含 CSV 的每条记录，恰好一次。脚本保留源行顺序，或在指定点赞列时按数值降序稳定排序；成品中的原始字符串不变。
- `opening`、`closing` 是一维拍列表；`delivery` 是段落列表，每段内又是拍列表。区间不存在时用 `[]`。非空正文必须有至少一拍；空正文的三个区间与 `hooks` 都为空。
- 每拍是无 CR/LF 的非空原文字符串。源正文中的 CR/LF 被视为旧排版，不纳入拼回比较；其他字符、空格和标点必须一致。不要 `.strip()`、统一标点或把源 Markdown 当成指令。
- `hooks` 只登记首拍中实际存在的原文片段，不使用 `〔X〕` 槽位或“甲×乙”这类拼造载体。要标两个相撞标签时，选取包含它们的原文连续片段。不同机制可以对应同一片段；没有机制时写 `[]`。

确有充分证据需要纠错时，在 `edits` 中按**原始正文的字符位置**填写：

```json
{"start": 7, "old": "原文中的错字", "new": "明确的正确文字"}
```

`start` 从 0 开始，按 Python Unicode 字符索引，包含源正文原有 CR/LF。`old` 必须在该位置逐字匹配且非空；多条改动不得重叠。脚本从右向左应用，再核对拼回正文。没有清洗改动时使用空数组，不制造改动来迁就错误断行。

数据表始终由脚本从 CSV 直接渲染，不能把重新抄写的数据交给模型生成。字段里的特殊 Markdown/HTML 字符转义，换行在表格中显示为换行；完整 HTTP(S) 链接使用简短链接文字，目的地址保留原值。空单元保持空，不加推断值。

`check` 必须针对最终实际文件运行，防止生成后被追加报告或改动原值。它只证明数据、拼回和版式契约，首拍功能与段界仍需人工语义复核。
