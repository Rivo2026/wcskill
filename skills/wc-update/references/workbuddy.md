# WorkBuddy 安装与更新

在 WorkBuddy 中收到“帮我更新 wcskill”时使用本分支，不套用 Codex 的 npx 命令，也不把 CodeBuddy 当成 WorkBuddy。

## 执行

1. 读取当前 Skill 所在位置。用户级默认 `~/.workbuddy/skills/`；若实际读取自其他位置，确认它是当前有效安装目录后用 `--target` 指向该目录。保留当前安装范围，不因为一个任意工作目录存在就擅自创建项目级入口。
2. 使用本 Skill 随附的 `scripts/workbuddy_install.py`，默认从官方 GitHub 下载最新版。需要 Python 3.9+，不依赖 npx、Node.js、Git 或其他 Python 包。macOS/Linux 用 `python3`，Windows 优先用 `py -3`；使用实际可用的 Python 解释器。

   ```bash
   python3 /实际安装路径/wc-update/scripts/workbuddy_install.py
   ```

   命令中的脚本路径必须替换为本轮实际读取到的位置；路径有空格时正确引用。首次从下载包安装，可在解压目录运行 `python3 install.py --source .`。

3. 安装器先准备全部文件、备份同名旧内容，然后替换并逐文件核对。默认备份与版本记录位于 `~/.wcskill/workbuddy/`，用户的其他存档保持原状。原来的符号链接会替换为 WorkBuddy 专用副本，链接源文件不被改写；本地个性化修改留在备份中，不自动合并。
4. 若返回 `unmanaged_conflicts` 或提示未标识来源的同名 Skill，读取对应入口和链接目标。只有已有证据确认它们属于用户的旧 wcskill，才能使用 `--replace-existing` 接管；其他来源的同名工具必须先向用户说明冲突。缺少权限、网络或运行环境时如实报告。
5. 以退出状态与 JSON 结果为准：`updated` 表示安装、读回和版本记录完成；`current` 表示文件已是最新版。失败时会尝试恢复原入口，恢复不完整会给出具体错误及备份目录；不要将失败说成成功。完成后报版本、实际目录和需要时的备份位置，提醒新建对话。

## 只检查

用户只问“有没有新版”“目前是什么版本”时运行同一脚本的 `--check`。它下载并比较正式文件，但不修改安装目录、备份或安装记录。`latest_version` 是远端版本，不能称为已经安装的版本；各已装 Skill 的 `wcskill-source.json` 与安装记录提供本地版本，缺失时如实说明未知。

```bash
python3 /实际安装路径/wc-update/scripts/workbuddy_install.py --check
```

不要从 WorkBuddy 登录状态推断文件已加载。安装后在技能列表确认 `wc`、`wc-update` 等已显示并启用；界面或对话不可访问时，区分“文件安装已验证”和“客户端调用尚未验证”。
