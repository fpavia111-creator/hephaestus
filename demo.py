#!/usr/bin/env python3
"""End-to-end demo: lint -> fix -> triggers -> build .
Runs on Windows/macOS/Linux:  python demo.py   (uses a temp folder, touches nothing else)."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
S = ROOT / "free" / "skill-shipper" / "scripts" / "skillship.py"


def run(title, *args, env=None):
    print(f"\n=== {title}\n$ skillship {' '.join(str(a) for a in args[1:])}")
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, env=env)
    print((r.stdout + r.stderr).rstrip(), f"\n[exit {r.returncode}]")
    return r


tmp = Path(tempfile.mkdtemp(prefix="skillship-demo-"))
src = tmp / "invoice-chaser"
shutil.copytree(ROOT / "examples" / "invoice-chaser", src)
run("1. lint the original (weak) skill", S, "lint", src)
run("2. offline trigger check, original description", S, "triggers", src)

md = src / "SKILL.md"
fixed = (ROOT / "examples" / "fixed-description.txt").read_text(encoding="utf-8").strip()
t = md.read_text(encoding="utf-8").replace("Invoice-Chaser", "invoice-chaser") \
    .replace("Helps with invoices.", fixed).replace("author: kurt", "license: MIT")
t += ("\n## Steps\n1. Run `python scripts/overdue.py invoices.csv` to list overdue rows.\n"
      "2. Draft one reminder per client; firmer tone after 30 and 60 days overdue.\n"
      "3. Show drafts to the user. Never send email yourself.\n")
md.write_text(t, encoding="utf-8")
(src / "references").mkdir()
(src / "references" / "tone.md").write_text("# Tone\nPolite, specific: amount, invoice number, due date.\n", encoding="utf-8")
print("\n=== applied fixes: lowercase name, rewritten description, license, steps, references/tone.md")
run("3. lint after fixes", S, "lint", src)
run("4. trigger check after fixes", S, "triggers", src)
run("5. build release", S, "build", src, "--version", "1.0.0", "--author", "Kurt Francisco", "--out", tmp / "dist")
print("\nfiles:", *sorted(p.relative_to(tmp).as_posix() for p in (tmp / "dist").rglob("*") if p.is_file()), sep="\n  ")

print("\nPro (watermark, identify, listing) is sold separately: <LS_URL>")
shutil.rmtree(tmp)
