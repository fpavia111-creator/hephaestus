import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "free" / "skill-shipper" / "scripts"))
import skillship as ss  # noqa: E402

GOOD_DESC = ("Finds overdue unpaid invoices in a CSV and drafts payment reminder emails. "
             "Use when the user wants to chase late payments or overdue invoices.")
BODY = "\n# Title\n\n" + "Step text explaining the workflow in detail. " * 8 + "\nRun `scripts/run.py`.\n"


def make_skill(root: Path, name="demo-skill", desc=GOOD_DESC, extra_fm="license: MIT\n", body=BODY, files=("scripts/run.py",)):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n{extra_fm}---\n{body}", encoding="utf-8")
    for f in files:
        (d / f).parent.mkdir(parents=True, exist_ok=True)
        (d / f).write_text("print('hi')\n", encoding="utf-8")
    return d


def codes(res):
    return {f["code"] for f in res["findings"]}


class FrontmatterTests(unittest.TestCase):
    def test_folded_block_and_metadata(self):
        meta, body, err = ss.parse_frontmatter('---\nname: x\ndescription: >\n  line one\n  line two\nmetadata:\n  version: "1.0"\n---\nhello')
        self.assertIsNone(err)
        self.assertEqual(meta["description"], "line one line two")
        self.assertEqual(meta["metadata"], {"version": "1.0"})
        self.assertEqual(body, "hello")

    def test_crlf_and_bom(self):
        meta, _, err = ss.parse_frontmatter("\ufeff---\r\nname: x\r\ndescription: 'q'\r\n---\r\nb")
        self.assertIsNone(err)
        self.assertEqual(meta, {"name": "x", "description": "q"})

    def test_missing_open(self):
        self.assertIsNotNone(ss.parse_frontmatter("# no fm")[2])

    def test_unclosed(self):
        self.assertIsNotNone(ss.parse_frontmatter("---\nname: x\n")[2])


class LintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_good_skill_passes_clean(self):
        res = ss.lint(make_skill(self.root))
        self.assertTrue(res["ok"], res["findings"])
        self.assertEqual(res["findings"], [])

    def test_missing_skill_md(self):
        (self.root / "x").mkdir()
        self.assertIn("E001", codes(ss.lint(self.root / "x")))

    def test_bad_names(self):
        for bad in ("Bad-Name", "-lead", "a--b", "x" * 65):
            d = self.root / bad
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {bad}\ndescription: {GOOD_DESC}\n---\n{BODY}", encoding="utf-8")
            self.assertIn("E011", codes(ss.lint(d)), bad)

    def test_name_folder_mismatch(self):
        d = make_skill(self.root)
        d2 = d.rename(self.root / "other")
        self.assertIn("E012", codes(ss.lint(d2)))

    def test_description_rules(self):
        self.assertIn("E021", codes(ss.lint(make_skill(self.root, "a1", desc="Use when x. " + "y" * 1100))))
        c = codes(ss.lint(make_skill(self.root, "a2", desc="I can help with invoices.")))
        self.assertTrue({"W022", "W023", "W024"} <= c)

    def test_missing_reference_and_backslash(self):
        d = make_skill(self.root, body=BODY + "\nSee `references\\tone.md`.\n")
        c = codes(ss.lint(d))
        self.assertIn("E051", c)
        self.assertIn("W050", c)

    def test_unknown_field_and_no_license(self):
        c = codes(ss.lint(make_skill(self.root, extra_fm="author: me\n")))
        self.assertIn("W032", c)
        self.assertIn("W070", c)

    def test_long_body(self):
        self.assertIn("W040", codes(ss.lint(make_skill(self.root, body=BODY + "x\n" * 600))))

    def test_env_file_warned(self):
        d = make_skill(self.root)
        (d / ".env").write_text("SECRET=1", encoding="utf-8")
        self.assertIn("W061", codes(ss.lint(d)))

    def test_cli_exit_codes(self):
        self.assertEqual(ss.main(["lint", str(make_skill(self.root))]), 0)
        bad = make_skill(self.root, "bad-one", desc="")
        self.assertEqual(ss.main(["lint", str(bad), "--json"]), 1)


class TriggerTests(unittest.TestCase):
    def test_overlap_scoring(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_skill(Path(t))
            (d / "triggers.json").write_text(json.dumps([
                {"query": "chase the overdue invoices for late payments", "should_trigger": True},
                {"query": "plan a birthday party menu", "should_trigger": False},
                {"query": "bake sourdough bread", "should_trigger": True},
            ]), encoding="utf-8")
            r = ss.trigger_check(d)
            self.assertEqual((r["passed"], r["total"]), (2, 3))
            self.assertFalse(r["rows"][2]["pass"])
            self.assertIn("sourdough", r["rows"][2]["missing_terms"])


class BoundaryTests(unittest.TestCase):
    def test_do_not_use_terms_count_against(self):
        with tempfile.TemporaryDirectory() as t:
            desc = GOOD_DESC + " Do NOT use for cold outreach or creating new invoices."
            d = make_skill(Path(t), desc=desc)
            (d / "triggers.json").write_text(json.dumps([
                {"query": "write a cold outreach email to a prospect", "should_trigger": False},
                {"query": "chase overdue invoices with reminder emails", "should_trigger": True}]), encoding="utf-8")
            r = ss.trigger_check(d)
            self.assertEqual(r["rows"][0]["score"], 0.0)
            self.assertEqual(r["passed"], 2)


class BuildTests(unittest.TestCase):
    def test_build_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = make_skill(root)
            (d / "triggers.json").write_text("[]", encoding="utf-8")
            (d / "__pycache__").mkdir()
            (d / "__pycache__" / "x.pyc").write_bytes(b"0")
            m = ss.build(d, root / "dist", "1.2.0", "Kurt Francisco")
            out = root / "dist" / "demo-skill-1.2.0"
            self.assertTrue((out / "skill" / "demo-skill" / "SKILL.md").is_file())
            self.assertFalse((out / "skill" / "demo-skill" / "triggers.json").exists())
            self.assertFalse((out / "skill" / "demo-skill" / "__pycache__").exists())
            with zipfile.ZipFile(out / "demo-skill-claude-ai.zip") as z:
                names = z.namelist()
            self.assertIn("demo-skill/SKILL.md", names)
            self.assertTrue(all("\\" not in n for n in names))
            mp = json.loads((out / "plugin-marketplace/.claude-plugin/marketplace.json").read_text())
            self.assertEqual(mp["plugins"][0]["source"], "./plugins/demo-skill")
            pj = json.loads((out / "plugin-marketplace/plugins/demo-skill/.claude-plugin/plugin.json").read_text())
            self.assertEqual(pj["version"], "1.2.0")
            self.assertTrue((out / "plugin-marketplace/plugins/demo-skill/skills/demo-skill/SKILL.md").is_file())
            self.assertTrue((root / "dist" / "demo-skill-1.2.0.zip").is_file())
            self.assertEqual(len(m["release_sha256"]), 64)

    def test_build_refuses_lint_errors(self):
        with tempfile.TemporaryDirectory() as t:
            d = make_skill(Path(t), desc="")
            with self.assertRaises(SystemExit):
                ss.build(d, Path(t) / "dist")


class ShippedSkillTests(unittest.TestCase):
    def test_own_skills_lint_clean(self):
        for d in (ROOT / "free" / "skill-shipper",):
            res = ss.lint(d)
            self.assertTrue(res["ok"], res["findings"])
            self.assertEqual([f for f in res["findings"] if f["level"] == "warn"], [], d)


if __name__ == "__main__":
    unittest.main()
