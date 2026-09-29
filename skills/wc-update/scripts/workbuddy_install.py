#!/usr/bin/env python3
"""Install/update the official wcskill collection for WorkBuddy. Python 3.9+."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile

REPOSITORY = "Rivo2026/wcskill"
ARCHIVE_URL = "https://codeload.github.com/Rivo2026/wcskill/zip/refs/heads/main"
MARKER = "wcskill-source.json"
DESCRIPTIONS = {
    "wc": ("望川内容工具箱入口，选择内容创作、研究与更新工具。", "Route content creation, research and toolkit update requests."),
    "wc-author-voice": ("从多篇文案提取作者的思维方式、论证逻辑和表达习惯。", "Extract an author's thinking, reasoning and expression patterns from their writing."),
    "wc-check": ("检查或修订完整口播稿，保留已确认的观点和事实边界。", "Review or revise a complete spoken script while preserving its intent and facts."),
    "wc-content-prep": ("整理内容素材并通过讨论形成有依据的写作判断。", "Prepare content material and develop evidence-based writing decisions."),
    "wc-draft": ("根据材料和确认的框架撰写完整口播正文。", "Draft a complete spoken script from supplied material and an approved framework."),
    "wc-hook": ("根据已有正文设计并衔接短视频开头；当前为试用框架。", "Create and connect a short-video opening from an existing script; preview framework."),
    "wc-organize": ("保留短视频 CSV 数据，整理口播断行与首拍分析。", "Organize short-video CSV scripts while preserving original data."),
    "wc-dy-hook": ("从对标内容提炼并生成抖音短视频开头。", "Analyze reference videos and generate Douyin opening hooks."),
    "wc-xhs-title": ("根据话题和受众生成小红书标题。", "Generate Xiaohongshu titles for a topic and audience."),
    "wc-research": ("组织思想家模拟圆桌，研究问题并持续学习。", "Research questions through simulated interdisciplinary discussions."),
    "wc-position": ("结合业务和本人经历制定人设定位方案。", "Create persona positioning proposals from business and personal experience."),
    "wc-update": ("更新望川工具箱，备份本地修改并保留用户存档。", "Update the Wangchuan toolkit with backups of local changes."),
}


def hashes(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def remove_entry(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def skill_text(text, name, version):
    """Keep instructions unchanged; add WorkBuddy import metadata only."""
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f"{name}: missing YAML frontmatter")
    front, body = parts[1], parts[2]
    declared = re.search(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", front, re.M)
    if not declared or declared.group(1) != name:
        raise ValueError(f"{name}: folder/name mismatch")
    if name not in DESCRIPTIONS:
        raise ValueError(f"{name}: add WorkBuddy descriptions before publishing")
    front = re.sub(r"^(description_zh|description_en|version|author):[^\n]*\n?", "", front, flags=re.M)
    zh, en = DESCRIPTIONS[name]
    fields = {"description_zh": zh, "description_en": en, "version": version, "author": "望川"}
    extra = "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items())
    return "---\n" + front.strip() + "\n" + extra + "\n---" + body


def catalog(source):
    version = (source / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid release VERSION")
    names = sorted(p.parent.name for p in (source / "skills").glob("*/SKILL.md"))
    if not names or "wc" not in names or "wc-update" not in names:
        raise ValueError("Source is not a complete wcskill release")
    return version, names


def prepare_skill(source, name, version, dest):
    original = source / "skills" / name
    if original.is_symlink() or any(p.is_symlink() for p in original.rglob("*")):
        raise ValueError(f"{name}: source symlinks are not supported")
    shutil.copytree(original, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    file = dest / "SKILL.md"
    file.write_text(skill_text(file.read_text(encoding="utf-8"), name, version), encoding="utf-8")
    (dest / MARKER).write_text(json.dumps({"repository": REPOSITORY, "skill": name, "version": version}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def source_release(local=None):
    if local is not None:
        yield Path(local).expanduser().resolve()
        return
    with tempfile.TemporaryDirectory(prefix="wcskill-download-") as temp:
        root = Path(temp)
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "wcskill-workbuddy-installer"})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError("Release archive exceeds 32 MiB")
        archive = root / "release.zip"
        archive.write_bytes(data)
        with zipfile.ZipFile(archive) as zipped:
            infos = zipped.infolist()
            if sum(i.file_size for i in infos) > 128 * 1024 * 1024:
                raise ValueError("Expanded archive exceeds 128 MiB")
            for info in infos:
                if "\\" in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("Unsupported archive entry")
                target = (root / "unpacked" / info.filename).resolve()
                if not target.is_relative_to(root / "unpacked"):
                    raise ValueError("Archive path leaves extraction directory")
            zipped.extractall(root / "unpacked")
        candidates = list((root / "unpacked").glob("*/VERSION"))
        if len(candidates) != 1:
            raise ValueError("Cannot locate release root")
        yield candidates[0].parent


def owned(path, name):
    try:
        marker = json.loads((path / MARKER).read_text(encoding="utf-8"))
        return marker.get("repository") == REPOSITORY and marker.get("skill") == name
    except (OSError, ValueError):
        return False


def install(source, target, state, replace_existing=False, check=False):
    source, target, state = (Path(p).expanduser().resolve() for p in (source, target, state))
    if state.is_relative_to(target) or target.is_relative_to(state):
        raise ValueError("State/backups and skills directory must be separate")
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("Source and installation directory must be separate")
    version, names = catalog(source)
    with tempfile.TemporaryDirectory(prefix="wcskill-prepare-") as temp:
        prepared = Path(temp)
        for name in names:
            prepare_skill(source, name, version, prepared / name)
        changed = [name for name in names if not (target / name).is_dir() or hashes(target / name) != hashes(prepared / name)]
        conflicts = [name for name in names if os.path.lexists(target / name) and not owned(target / name, name)]
        if check:
            return {"status": "update_available" if changed else "current", "latest_version": version,
                    "target": str(target), "changed": changed, "unmanaged_conflicts": conflicts}
        if conflicts and not replace_existing:
            raise ValueError("Unmanaged same-name skills: " + ", ".join(conflicts) + ". Confirm they are old wcskill copies before using --replace-existing.")
        if not changed:
            return {"status": "current", "version": version, "target": str(target), "skills": names}
        target.parent.mkdir(parents=True, exist_ok=True)
        state.mkdir(parents=True, exist_ok=True)
        scope = state / "workbuddy" / hashlib.sha256(str(target).encode()).hexdigest()[:16]
        scope.mkdir(parents=True, exist_ok=True)
        lock = scope / ".install.lock"
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            return apply_install(prepared, target, scope, version, names, changed)
        finally:
            lock.unlink()


def apply_install(prepared, target, scope, version, names, changed):
    target.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-"), dir=scope))
    links = {}
    # Persistent copies preserve edits even when an old entry points to another checkout.
    for name in changed:
        old = target / name
        if old.is_symlink():
            links[name] = os.readlink(old)
        if old.is_dir():
            shutil.copytree(old, backup / name, symlinks=True)
        elif old.is_file():
            shutil.copy2(old, backup / name)
    (backup / "entry-links.json").write_text(json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
    touched = []
    # Keep the exact previous entries on the target volume until verification succeeds.
    with tempfile.TemporaryDirectory(prefix=".wcskill-stage-", dir=target.parent) as temp:
        staging = Path(temp)
        (staging / "old").mkdir()
        for name in changed:
            shutil.copytree(prepared / name, staging / name)
        try:
            for name in changed:
                previous = staging / "old" / name
                had_old = os.path.lexists(target / name)
                if had_old:
                    os.replace(target / name, previous)
                touched.append((name, had_old))
                os.replace(staging / name, target / name)
            for name in names:
                if hashes(target / name) != hashes(prepared / name):
                    raise RuntimeError(f"Readback differs: {name}")
            record = {"repository": REPOSITORY, "version": version, "target": str(target), "skills": names,
                      "installed_at": datetime.now(timezone.utc).isoformat(), "backup": str(backup)}
            pending = scope / "installed.json.tmp"
            pending.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(pending, scope / "installed.json")
        except BaseException as error:
            failures = []
            for name, had_old in reversed(touched):
                try:
                    remove_entry(target / name)
                    if had_old:
                        os.replace(staging / "old" / name, target / name)
                except OSError as rollback_error:
                    failures.append(f"{name}: {rollback_error}")
            if failures:
                # Preserve exact old entries even when rollback cannot finish.
                shutil.copytree(staging / "old", backup / "rollback-entries", symlinks=True)
                raise RuntimeError(f"Install failed: {error}; rollback incomplete: {failures}; backup: {backup}") from error
            raise RuntimeError(f"Install failed; previous entries restored. Backup: {backup}. Cause: {error}") from error
    return {"status": "updated", **record, "changed": changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Use a downloaded wcskill repository/bundle instead of GitHub")
    parser.add_argument("--target", type=Path, default=Path.home() / ".workbuddy" / "skills")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".wcskill")
    parser.add_argument("--replace-existing", action="store_true", help="Adopt confirmed old wcskill entries lacking source markers; backup first")
    parser.add_argument("--check", action="store_true", help="Inspect available update without changing skills or state")
    args = parser.parse_args()
    try:
        with source_release(args.source) as source:
            result = install(source, args.target, args.state_dir, args.replace_existing, args.check)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as error:
        parser.exit(1, f"wcskill: {error}\n")


if __name__ == "__main__":
    main()
