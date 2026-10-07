---
name: wc-update
description: 更新望川 wcskill 工具箱，保留其他 Skill 与用户存档。用户说“帮我更新 wcskill”“升级 wcskill”、检查 wcskill 版本，或在明确的更新提醒后回复 1 时使用；只问版本时不安装。
---

# wc-update：更新 wcskill

用户已经明确要求更新 wcskill，或在上一条 wcskill 更新提醒后回复了 `1`。两种情况都直接执行更新，不再做第二次文字确认；宿主若要求 Shell 权限，由用户在宿主的权限窗口中决定。

只有上一条助手回复明确包含 wcskill 更新提醒时，单独回复的 `1` 才代表更新。缺少这段上下文时，不要自行解释数字含义。

## 更新范围

- 只更新官方仓库 `Rivo2026/wcskill`。
- 保留用户在 `~/.wcskill/` 中的存档、报告和决策记录。
- 不更新用户安装的其他 Skill。
- 不创建后台任务、定时任务或 Agent Hook。

## 执行步骤

**WorkBuddy 分支**：当前客户端为 WorkBuddy、当前 Skill 安装路径位于 `.workbuddy/skills/`，或用户明确要求更新 WorkBuddy 中的 wcskill 时，读取 [WorkBuddy 安装与更新](references/workbuddy.md)，使用随附安装器完成后结束。本节后续的 Skills CLI 命令适用于其已支持的其他客户端。

1. 从当前会话和实际 Skill 路径确定客户端及安装范围，读取当前入口，解析符号链接指向。用户级安装沿用用户级；项目级安装在原项目目录执行，不加 `-g`。Codex 使用 `--agent codex`，Claude Code 使用 `--agent claude-code`；其他客户端先核对 Skills CLI 支持的名称。首次安装默认当前客户端的用户级目录。目录确有歧义且会改变覆盖范围时才询问，不重复确认已明确的更新意图。

2. 查看官方仓库的 Skill 清单，备份目标范围内将被覆盖的同名文件夹和入口，包括符号链接指向及本地修改；备份放在安装目录外，记录原路径和本来不存在的目标。无法判断是否被修改时也备份，不能仅备份入口文件。`~/.wcskill/` 中的用户存档及其他仓库的 Skill 不参与覆盖；遇到同名但属于其他来源的工具时，先报告具体冲突，不能视为本工具箱的旧版。

3. 使用 Skills CLI 同步本仓库的全部正式 Skill。以下是 Codex 用户级安装的命令；根据步骤 1 调整客户端和范围，保留原先使用的复制方式（原来是独立副本时加 `--copy`）：

   ```bash
   DISABLE_TELEMETRY=1 npx -y skills add Rivo2026/wcskill --skill '*' --agent codex -g --yes
   ```

   `--skill '*'` 选择本仓库全部 Skill，`--yes` 跳过安装器的重复确认。不要使用 `--all`，它也会选中所有客户端。需要可用的 Git、Node.js 与 npm/npx；缺失或宿主拒绝执行时如实报告未完成，不宣称更新成功。

4. 核对命令退出状态、安装器结果和目标目录：正式清单中的每个 `SKILL.md` 及附属文件已落盘，入口已包含更新工具，并且没有安装失败的项目。只有实际安装成功且读回一致后，才记录更新时间；时间不是版本号：

   ```bash
   node -e 'const fs=require("node:fs"),os=require("node:os"),path=require("node:path");const dir=path.join(os.homedir(),".wcskill");fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,"update_check_at"),String(Math.floor(Date.now()/1000))+"\n");'
   ```

5. 告诉用户更新已完成；若有本地修改，给出备份位置，不把“已备份”说成“已合并进新版”。当前对话可能仍加载旧规则，提醒用户新建一次对话后使用新能力。

6. 命令或读回失败时，不记录成功时间。若安装器已改动文件，按本次备份恢复受影响的同名文件夹及入口；仅清理确认由本次失败安装新建的目标，不扩大到其他 Skill。读回后报告失败原因及恢复结果；恢复不完整时明确哪些位置仍待处理，不谎报已经恢复。不要把完整终端日志直接贴给用户，除非用户要求。

## 回复格式

成功：

> wcskill 已更新完成。当前对话如果还没有读取到新能力，新建一次对话后即可使用。

失败：

> wcskill 没有更新完成：{简短原因}。处理完 {权限或网络问题} 后，再说一次「更新 wcskill」。

## 边界

- 用户只问版本、更新内容或是否需要更新时，只读取官方 `VERSION`、变更及当前安装记录，不执行安装命令。没有本地版本记录时说明当前版本未知，不能用更新时间推算版本。
- 用户明确要求检查更新且希望实际同步时，按本 Skill 更新。
- 不运行不带范围的 `npx skills update`，避免更新其他来源的 Skill；本工具固定使用指定仓库的 `skills add`。

---

完成当前任务后直接结束。只有用户明确询问下一步，且当前环境已经安装 `/wc` 时，简短提示：「下一步不确定时，可以输入 `/wc`。」

安装命令使用 `DISABLE_TELEMETRY=1` 关闭 Skills CLI 的匿名使用统计；这不会改变工具的安装或更新能力。
