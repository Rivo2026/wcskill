import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workbuddy", ROOT / "skills/wc-update/scripts/workbuddy_install.py")
wb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wb)


class WorkBuddyInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "profile/.workbuddy/skills"
        self.state = self.root / "profile/.wcskill"
        self.make_release("2.3.0", "first")

    def make_release(self, version, body):
        self.source.mkdir(exist_ok=True)
        (self.source / "VERSION").write_text(version)
        for name in ["wc", "wc-update"]:
            folder = self.source / "skills" / name
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test skill\n---\n{body}\n")
            (folder / "references").mkdir(exist_ok=True)
            (folder / "references/method.md").write_text(body)

    def install(self, **options):
        return wb.install(self.source, self.target, self.state, **options)

    def test_install_then_update_preserves_other_skills_notes_and_backup(self):
        first = self.install()
        self.assertEqual(first["status"], "updated")
        other = self.target / "other/SKILL.md"
        other.parent.mkdir()
        other.write_text("Unrelated skill")
        notes = self.state / "student-notes.md"
        notes.write_text("Student notes")
        edited = self.target / "wc/references/method.md"
        edited.write_text("Local method")
        self.make_release("2.4.0", "second")
        result = self.install()
        self.assertEqual(result["version"], "2.4.0")
        self.assertEqual(edited.read_text(), "second")
        self.assertEqual((Path(result["backup"]) / "wc/references/method.md").read_text(), "Local method")
        self.assertEqual(other.read_text(), "Unrelated skill")
        self.assertEqual(notes.read_text(), "Student notes")
        self.assertEqual(self.install()["status"], "current")

    def test_unmanaged_conflict_does_not_write_state_or_replace_content(self):
        existing = self.target / "wc/SKILL.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("Someone else's skill")
        with self.assertRaisesRegex(ValueError, "Unmanaged"):
            self.install()
        self.assertEqual(existing.read_text(), "Someone else's skill")
        self.assertFalse(self.state.exists())

    def test_check_is_read_only(self):
        before = wb.hashes(self.root)
        result = self.install(check=True)
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(wb.hashes(self.root), before)
        self.assertFalse(self.target.exists())
        self.assertFalse(self.state.exists())

    def test_adopt_symlink_preserves_source_and_backups(self):
        original = self.root / "existing-repo/wc"
        original.mkdir(parents=True)
        (original / "SKILL.md").write_text("Old personalized wc")
        self.target.mkdir(parents=True)
        (self.target / "wc").symlink_to(original, target_is_directory=True)
        result = self.install(replace_existing=True)
        self.assertFalse((self.target / "wc").is_symlink())
        self.assertEqual((original / "SKILL.md").read_text(), "Old personalized wc")
        self.assertEqual((Path(result["backup"]) / "wc/SKILL.md").read_text(), "Old personalized wc")
        links = json.loads((Path(result["backup"]) / "entry-links.json").read_text())
        self.assertEqual(links["wc"], str(original))

    def test_mid_install_failure_restores_every_previous_entry_and_record(self):
        first = self.install()
        before = wb.hashes(self.target)
        record = next(self.state.rglob("installed.json"))
        record_before = record.read_bytes()
        self.make_release("2.4.0", "second")
        real_replace = wb.os.replace

        def fail_second_skill(source, target):
            if Path(source).name == "wc-update" and Path(source).parent.name.startswith(".wcskill-stage-"):
                raise OSError("Simulated disk write failure")
            return real_replace(source, target)

        with patch.object(wb.os, "replace", side_effect=fail_second_skill):
            with self.assertRaisesRegex(RuntimeError, "previous entries restored"):
                self.install()
        self.assertEqual(wb.hashes(self.target), before)
        self.assertEqual(record.read_bytes(), record_before)
        self.assertFalse(list(self.state.rglob(".install.lock")))

    def test_failed_first_install_removes_new_entries(self):
        real_replace = wb.os.replace

        def fail_second_skill(source, target):
            if Path(source).name == "wc-update" and Path(source).parent.name.startswith(".wcskill-stage-"):
                raise OSError("Simulated first-install failure")
            return real_replace(source, target)

        with patch.object(wb.os, "replace", side_effect=fail_second_skill):
            with self.assertRaises(RuntimeError):
                self.install()
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertFalse(list(self.state.rglob("installed.json")))

    def test_workbuddy_metadata_keeps_original_instructions_and_is_idempotent(self):
        original = "---\nname: wc\ndescription: |\n  A multiline description\n  with another line\n---\n# Original instructions\n\nKeep these.\n"
        adapted = wb.skill_text(original, "wc", "2.3.0")
        self.assertEqual(adapted.split("---", 2)[2], original.split("---", 2)[2])
        self.assertIn('description_en:', adapted)
        self.assertEqual(wb.skill_text(adapted, "wc", "2.3.0"), adapted)


class PackageTests(unittest.TestCase):
    def test_all_import_archives_and_offline_bundle(self):
        spec = importlib.util.spec_from_file_location("build_workbuddy", ROOT / "scripts/build_workbuddy.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as temp:
            outputs = builder.build(Path(temp))
            version, names = wb.catalog(ROOT)
            self.assertEqual(len(outputs), len(names) + 3)
            for name in names:
                with zipfile.ZipFile(Path(temp) / f"{name}-workbuddy-{version}.zip") as zipped:
                    source = ROOT / "skills" / name
                    text = zipped.read(f"{name}/SKILL.md").decode()
                    self.assertEqual(text.split("---", 2)[2], (source / "SKILL.md").read_text().split("---", 2)[2])
                    for file in source.rglob("*"):
                        if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc" and file.name != "SKILL.md":
                            self.assertEqual(zipped.read(f"{name}/" + file.relative_to(source).as_posix()), file.read_bytes())
            with zipfile.ZipFile(Path(temp) / f"wcskill-workbuddy-{version}.zip") as zipped:
                self.assertIn("wcskill-workbuddy/install.py", zipped.namelist())
                self.assertIn("wcskill-workbuddy/安装说明.md", zipped.namelist())
            with zipfile.ZipFile(Path(temp) / f"wcskill-skillhub-{version}.zip") as market:
                self.assertIn("wcskill/SKILL.md", market.namelist())
                self.assertLessEqual(len(market.namelist()), 200)
                for name in names:
                    with zipfile.ZipFile(Path(temp) / f"{name}-workbuddy-{version}.zip") as single:
                        for member in single.namelist():
                            self.assertEqual(market.read("wcskill/skills/" + member), single.read(member))


if __name__ == "__main__":
    unittest.main()
