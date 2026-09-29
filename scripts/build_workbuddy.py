#!/usr/bin/env python3
"""Build WorkBuddy imports and one offline installer bundle from the same skills."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workbuddy_install", ROOT / "skills/wc-update/scripts/workbuddy_install.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def archive(folder, target):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zipped:
        for file in sorted(folder.rglob("*")):
            if file.is_file():
                info = zipfile.ZipInfo(file.relative_to(folder.parent).as_posix(), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, file.read_bytes())


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    version, names = INSTALLER.catalog(ROOT)
    results = []
    with tempfile.TemporaryDirectory(prefix="wcskill-package-") as temp:
        root = Path(temp)
        bundle = root / "wcskill-workbuddy"
        (bundle / "skills").mkdir(parents=True)
        for name in names:
            folder = bundle / "skills" / name
            INSTALLER.prepare_skill(ROOT, name, version, folder)
            dest = output / f"{name}-workbuddy-{version}.zip"
            archive(folder, dest)
            results.append(dest)
        shutil.copy2(ROOT / "skills/wc-update/scripts/workbuddy_install.py", bundle / "install.py")
        (bundle / "VERSION").write_text(version + "\n", encoding="utf-8")
        (bundle / "安装说明.md").write_text(
            "# 望川工具箱 · WorkBuddy\n\n将本文件夹交给 WorkBuddy，并说：\n\n"
            "> 请读取安装说明，用 Python 运行 install.py --source .，将十二个 Skill 安装到 WorkBuddy。\n\n"
            "也可在解压后的本目录运行 `python3 install.py --source .`；Windows 可用 `py -3 install.py --source .`。\n"
            "需要 Python 3.9 或更新版本。默认安装到用户目录的 .workbuddy/skills。\n"
            "如遇未标识来源的同名目录，先确认它们是旧版望川工具箱，再加 --replace-existing；安装器会先备份。\n\n"
            "安装后在技能列表确认启用，再新建对话，说‘望川工具箱有哪些工具’。以后说‘帮我更新 wcskill’即可走更新流程。\n"
            "圆桌角色是理论模拟；完整执行需当前会话允许子代理，没有该能力时会明确说明降级。\n",
            encoding="utf-8",
        )
        dest = output / f"wcskill-workbuddy-{version}.zip"
        archive(bundle, dest)
        results.append(dest)
        # A single market entry contains the entire toolkit, usable without
        # registering seven separate skills or running an installation hook.
        market = root / "wcskill"
        shutil.copytree(bundle / "skills", market / "skills")
        shutil.copy2(bundle / "VERSION", market / "VERSION.md")
        shutil.copy2(ROOT / "LICENSE", market / "LICENSE.md")
        entry = (ROOT / "scripts/templates/skillhub-entry.md").read_text(encoding="utf-8")
        _, front, body = entry.split("---", 2)
        fields = {"description_zh": "望川内容创作工具箱：内容准备、作者思维提取、口播写作、开头生成、全稿检查、语料整理、标题、研究、人设定位与更新，整套安装。",
                  "description_en": "Wangchuan's complete toolkit for content preparation, author analysis, script drafting, hooks, review, organization, titles, research, positioning and updates.",
                  "version": version, "author": "望川"}
        extra = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items())
        (market / "SKILL.md").write_text("---\n" + front.strip() + "\n" + extra + "\n---" + body, encoding="utf-8")
        files = [p for p in market.rglob("*") if p.is_file()]
        if len(files) > 200 or sum(p.stat().st_size for p in files) > 10_000_000:
            raise ValueError("SkillHub package exceeds upload limits")
        dest = output / f"wcskill-skillhub-{version}.zip"
        archive(market, dest)
        results.append(dest)
    checksums = output / "SHA256SUMS.txt"
    checksums.write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in results), encoding="utf-8")
    return results + [checksums]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for result in build(parser.parse_args().output.resolve()):
        print(result)
