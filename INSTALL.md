# 安装 wcskill

wcskill 是望川的学员内容创作工具箱，官方仓库为 https://github.com/Rivo2026/wcskill 。本页供收到“安装 wcskill”的助手执行。

安装整套包含 `wc`、`wc-content-prep`、`wc-author-voice`、`wc-draft`、`wc-hook`、`wc-check`、`wc-organize`、`wc-dy-hook`、`wc-xhs-title`、`wc-research`、`wc-position`、`wc-update`。不要只安装总入口 `wc`，也不要让学员逐个安装。

## WorkBuddy

1. 检查 Python 3.9 或更新版本。macOS/Linux 通常使用 `python3`，Windows 通常使用 `py -3`；缺少运行环境时如实说明。
2. 从下面的官方地址把安装脚本下载到临时目录，读取脚本后执行。它会下载官方主分支，并一次安装当前正式的全部 Skill，无需 Git 或 Node.js。

   https://raw.githubusercontent.com/Rivo2026/wcskill/main/skills/wc-update/scripts/workbuddy_install.py

3. macOS/Linux 执行 `python3 <下载后的脚本绝对路径>`，Windows 执行 `py -3 <下载后的脚本绝对路径>`。默认目标为用户主目录下 `.workbuddy/skills/`。不要把 WorkBuddy 当作 CodeBuddy 安装到 `.codebuddy/skills/`。
4. 安装器会备份有来源标记的旧版内容并保留其他工具及用户存档。遇到来源不明的同名目录时先核对，不要直接覆盖；只有确认属于用户授权更新的旧版 wcskill，才使用 `--replace-existing`。
5. 读取安装结果与目标目录中的十二个 `SKILL.md`，报告实际结果；不需要试跑内容任务。提示学员新建对话使用。后续直接说“帮我更新 wcskill”。

如果原始文件下载不可用，可以下载 [整套发布包](https://github.com/Rivo2026/wcskill/releases/download/v2.5.0/wcskill-workbuddy-2.5.0.zip)，解压后在含 `install.py` 的目录执行 `python3 install.py --source .`（Windows 使用 `py -3`）。

## Codex / Claude Code

已具备 Git、Node.js 和 npm 时，按当前客户端执行：

```bash
DISABLE_TELEMETRY=1 npx -y skills add Rivo2026/wcskill --skill '*' --agent codex -g --yes
```

Claude Code 将 `--agent codex` 替换为 `--agent claude-code`。如果用户明确要求项目级安装，去掉 `-g` 并在指定项目中执行。更新已有安装时先按 [wc-update](skills/wc-update/SKILL.md) 保留本地修改。

## 关于名称检索

“安装 wcskill”是用户期望的自然语言入口，不是系统内置命令。助手需要搜索到本仓库或技能市场中的官方条目。找不到或存在同名来源时使用完整仓库链接定位，不要安装未经核对的同名包。
