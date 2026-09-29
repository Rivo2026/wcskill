---
name: wcskill
description: 望川学员内容创作工具箱整套入口。用户说安装或使用 wcskill、准备内容、提取作者思维、撰写口播、生成开头、检查稿件、整理短视频 CSV、起小红书标题、开展思想家研究圆桌、人设定位或更新 wcskill 时使用。包内完整包含十二个正式工具及其参考资料和脚本。
---

# wcskill · 望川内容创作工具箱

这是整套工具箱的市场分发入口，十二个正式工具已随包提供，不需要学员逐个安装。官方源：https://github.com/Rivo2026/wcskill 。

## 选择当前工具来源

以下相对路径均以本文件所在的 `wcskill` 文件夹为起点。默认使用包内 `skills/`，不要因为十二个工具没有分别注册在客户端列表里就报告未安装：读取对应文件即可执行，引用的资料和脚本相对于各自工具文件夹定位。

WorkBuddy 更新后，可能在本包的同级目录出现十二个独立工具。如果这十二个目录的 `wcskill-source.json` 均属于 `Rivo2026/wcskill`，版本一致且不低于本包 `VERSION.md`（按语义版本比较），整套改用同级目录中的新版。否则使用包内整套，避免混用版本或其他来源的同名工具。只在实际需要时读取版本标记和相应规则。

## 执行任务

先读取当前来源中的 [工具箱入口](skills/wc/SKILL.md)，沿用它的任务选择规则。明确任务后，读取相应工具并执行，不停在介绍名称，也不要求学员改用另一个命令：

| 用户的任务 | 包内规则 |
| --- | --- |
| 介绍工具、选择合适的工具 | [wc](skills/wc/SKILL.md) |
| 内容准备与观点共创 | [wc-content-prep](skills/wc-content-prep/SKILL.md) |
| 提取作者思维画像 | [wc-author-voice](skills/wc-author-voice/SKILL.md) |
| 根据材料写口播正文 | [wc-draft](skills/wc-draft/SKILL.md) |
| 为已有正文生成开头（试用框架） | [wc-hook](skills/wc-hook/SKILL.md) |
| 检查或修订完整稿件 | [wc-check](skills/wc-check/SKILL.md) |
| 短视频 CSV 保留数据、校对与口播断行 | [wc-organize](skills/wc-organize/SKILL.md) |
| 抖音对标开头分析与生成 | [wc-dy-hook](skills/wc-dy-hook/SKILL.md) |
| 小红书标题生成 | [wc-xhs-title](skills/wc-xhs-title/SKILL.md) |
| 思想家圆桌研究、知识讲解、持续学习 | [wc-research](skills/wc-research/SKILL.md) |
| 人设定位方案 | [wc-position](skills/wc-position/SKILL.md) |
| 更新工具箱或查看版本 | [wc-update](skills/wc-update/SKILL.md) |

“安装 wcskill”触发本入口时，先确认本包及表中十二个文件存在，说明整套已经装入，不重复安装或试跑内容任务。普通内容任务不需要网络下载才能加载本包；研究中需要核实资料时按研究工具的规则检索。

## WorkBuddy 的整套更新

用户明确要求“帮我更新 wcskill”时，沿用当前来源中 `wc-update` 的 WorkBuddy 安装器。市场包里的子工具路径属于内置资源，不是十二个工具的独立安装目录；安装目标是本 `wcskill` 文件夹的父目录（通常为 `~/.workbuddy/skills`），用 `--target` 明确传入。

```text
python3 <当前来源>/wc-update/scripts/workbuddy_install.py --target <本包父目录>
```

首次更新的当前来源是本包的 `skills/`；Windows 使用实际可用的 Python 3.9+，通常为 `py -3`。脚本下载官方最新十二个工具、备份并校验，不覆盖本包和用户存档。后续任务按前述来源规则使用新版。来源冲突遵循 `wc-update`，不要直接强制覆盖。只问版本时读取 `VERSION.md` 及有效来源的标记；需要检查远端时加 `--check`，不执行更新。

更新后分别报告十二个工具的有效版本和市场包版本，本包的旧 `VERSION.md` 不代表子工具更新失败。市场包自身可通过原安装市场更新。其他客户端按其安装范围执行 `wc-update` 的对应流程，不套用 WorkBuddy 的目录。
