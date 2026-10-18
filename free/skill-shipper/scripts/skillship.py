#!/usr/bin/env python3
"""skillship - lint, trigger-check and package an Agent Skill (SKILL.md) for distribution.

Standard library only. Works on Windows, macOS and Linux (Python 3.8+).

Commands:
  lint     <skill_dir> [--json]                 Validate against the Agent Skills spec + sellability checks
  triggers <skill_dir> [--table triggers.json]  Offline keyword-overlap check of a trigger table
  build    <skill_dir> [--out dist] [--version 1.0.0] [--author NAME]
                                                Produce Claude Code folder, claude.ai upload zip,
                                                Claude Code plugin + marketplace.json, and a manifest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
KNOWN_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools",
                # Claude Code extensions (code.claude.com/docs/en/skills)
                "when_to_use", "disable-model-invocation", "argument-hint", "model", "user-invocable"}
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", ".pytest_cache"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", ".env"}
STOP = set("a an the and or of to for in on with when use is are be this that it you your my me i "
           "do does can should will from by as at into about please".split())


class Finding(dict):
    def __init__(self, level: str, code: str, msg: str):
        super().__init__(level=level, code=code, message=msg)


# ---------------------------------------------------------------- frontmatter
def parse_frontmatter(text: str):
    """Minimal YAML subset parser: scalars, quoted strings, folded/literal blocks, one-level maps.
    Returns (dict, body, error_or_None)."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text, "SKILL.md must start with '---' on the first line"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text, "frontmatter is not closed with '---'"
    fm_lines, body = lines[1:end], "\n".join(lines[end + 1:])
    data: dict = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            return data, body, f"unexpected indentation on frontmatter line {i + 2}"
        if ":" not in line:
            return data, body, f"frontmatter line {i + 2} is not 'key: value'"
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        i += 1
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            while i < len(fm_lines) and (not fm_lines[i].strip() or fm_lines[i][0] in " \t"):
                block.append(fm_lines[i].strip())
                i += 1
            val = (" " if val.startswith(">") else "\n").join(b for b in block).strip()
        elif val == "":
            sub = {}
            while i < len(fm_lines) and fm_lines[i][:1] in (" ", "\t") and fm_lines[i].strip():
                k, _, v = fm_lines[i].strip().partition(":")
                sub[k.strip()] = _unquote(v.strip())
                i += 1
            val = sub
        else:
            val = _unquote(val)
        data[key] = val
    return data, body, None


def _unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


# ---------------------------------------------------------------- lint
def lint(skill_dir: Path):
    f: list = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return {"ok": False, "findings": [Finding("error", "E001", "SKILL.md not found (name is case-sensitive)")], "meta": {}}
    raw = skill_md.read_text(encoding="utf-8", errors="replace")
    meta, body, err = parse_frontmatter(raw)
    if err:
        f.append(Finding("error", "E002", err))
    name, desc = meta.get("name"), meta.get("description")
    if not name:
        f.append(Finding("error", "E010", "frontmatter 'name' is required"))
    elif not isinstance(name, str) or len(name) > 64 or not NAME_RE.match(name):
        f.append(Finding("error", "E011", f"name '{name}' must be 1-64 chars of a-z, 0-9 and single hyphens"))
    elif name != skill_dir.name:
        f.append(Finding("error", "E012", f"name '{name}' must match folder name '{skill_dir.name}'"))
    if not desc or not isinstance(desc, str):
        f.append(Finding("error", "E020", "frontmatter 'description' is required"))
    else:
        if len(desc) > 1024:
            f.append(Finding("error", "E021", f"description is {len(desc)} chars (max 1024)"))
        if len(desc) < 80:
            f.append(Finding("warn", "W022", "description under 80 chars; usually too vague to trigger reliably"))
        if not re.search(r"\b(use (this )?(skill )?(when|for|to)|when the user|trigger)", desc, re.I):
            f.append(Finding("warn", "W023", "description should say WHEN to use it (e.g. 'Use when ...')"))
        if re.search(r"\b(I can|I will|I'm)\b", desc):
            f.append(Finding("warn", "W024", "write the description in third person, not 'I can ...'"))
        if "<" in desc and ">" in desc:
            f.append(Finding("warn", "W025", "angle brackets in description can break some loaders/uploads"))
    comp = meta.get("compatibility")
    if isinstance(comp, str) and len(comp) > 500:
        f.append(Finding("error", "E030", "compatibility exceeds 500 chars"))
    if "metadata" in meta and not isinstance(meta["metadata"], dict):
        f.append(Finding("error", "E031", "metadata must be a key/value map"))
    for k in meta:
        if k not in KNOWN_FIELDS:
            f.append(Finding("warn", "W032", f"unknown frontmatter field '{k}' (ignored silently by Claude Code)"))
    n_lines = body.count("\n") + 1
    if n_lines > 500:
        f.append(Finding("warn", "W040", f"SKILL.md body is {n_lines} lines; keep under 500, move detail to references/"))
    if len(body.strip()) < 200:
        f.append(Finding("warn", "W041", "body is very short; buyers expect concrete steps, examples and edge cases"))
    # file references
    for ref in sorted(set(re.findall(r"(?:\]\(|`|\s)((?:scripts|references|assets)[/\\][^\s)`'\"]+)", body))):
        ref = ref.rstrip(".,:;")
        if "\\" in ref:
            f.append(Finding("warn", "W050", f"backslash path '{ref}' - use forward slashes for cross-platform"))
        if not (skill_dir / ref.replace("\\", "/")).exists():
            f.append(Finding("error", "E051", f"referenced file missing: {ref}"))
    if re.search(r"(?m)(^|\s)(/Users/|/home/[a-z]|[A-Z]:\\\\?Users)", body):
        f.append(Finding("warn", "W052", "absolute user path in body; will break on buyers' machines"))
    for p in skill_dir.rglob("*"):
        if p.is_symlink():
            f.append(Finding("error", "E060", f"symlink not allowed (breaks zips/Windows): {p.relative_to(skill_dir)}"))
        elif p.name in EXCLUDE_FILES:
            f.append(Finding("warn", "W061", f"'{p.name}' will be excluded from builds"))
    if not any(skill_dir.glob("LICENSE*")) and "license" not in meta:
        f.append(Finding("warn", "W070", "no license field or LICENSE file; buyers/marketplaces expect one"))
    ok = not any(x["level"] == "error" for x in f)
    return {"ok": ok, "findings": f, "meta": meta}


# ---------------------------------------------------------------- triggers
def _tokens(s: str):
    words = re.findall(r"[a-z0-9]+", s.lower())
    out = set()
    for w in words:
        if w in STOP or len(w) < 3:
            continue
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def trigger_check(skill_dir: Path, table_path: Path | None = None, threshold: float = 0.25):
    """Offline heuristic: token overlap between description and each query.
    This is NOT a model eval - it flags vocabulary gaps before you spend real `claude -p` runs."""
    meta, _, _ = parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    desc = (meta.get("description") or "") + " " + (meta.get("when_to_use") or "")
    # text after "Do NOT use for/when" is a boundary: its terms count against a match
    m = re.search(r"(?i)\bdo(?:n't| not) use\b", desc)
    pos_text, neg_text = (desc[:m.start()], desc[m.end():]) if m else (desc, "")
    neg = _tokens(neg_text)
    dtok = _tokens(pos_text) - neg
    table_path = table_path or (skill_dir / "triggers.json")
    cases = json.loads(Path(table_path).read_text(encoding="utf-8"))
    rows, passed = [], 0
    for c in cases:
        q = c["query"]
        qt = _tokens(q)
        score = max(0.0, (len(qt & dtok) - len(qt & neg)) / max(len(qt), 1))
        predicted = score >= threshold
        good = predicted == bool(c["should_trigger"])
        passed += good
        rows.append({"query": q, "should_trigger": c["should_trigger"], "score": round(score, 2),
                     "predicted": predicted, "pass": good, "missing_terms": sorted(qt - dtok)[:6]})
    return {"passed": passed, "total": len(cases), "threshold": threshold, "rows": rows}


# ---------------------------------------------------------------- build
def _copy_tree(src: Path, dst: Path):
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if any(part in EXCLUDE_DIRS for part in rel.parts) or p.name in EXCLUDE_FILES or p.is_symlink():
            continue
        if p.name == "triggers.json":
            continue
        t = dst / rel
        if p.is_dir():
            t.mkdir(parents=True, exist_ok=True)
        else:
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, t)


def _zip_dir(src: Path, zip_path: Path, prefix: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                # forward slashes always: Windows-made zips with backslashes fail on claude.ai/mac
                z.write(p, f"{prefix}/{p.relative_to(src).as_posix()}")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(skill_dir: Path, out: Path, version: str = "1.0.0", author: str = "Unknown"):
    res = lint(skill_dir)
    if not res["ok"]:
        raise SystemExit("lint errors - fix before building:\n" + "\n".join(
            f"  {x['code']} {x['message']}" for x in res["findings"] if x["level"] == "error"))
    meta = res["meta"]
    name, desc = meta["name"], meta["description"]
    out = out / f"{name}-{version}"
    if out.exists():
        shutil.rmtree(out)
    # 1) plain skill folder (Claude Code ~/.claude/skills, Codex, Cursor, OpenCode, etc.)
    folder = out / "skill" / name
    _copy_tree(skill_dir, folder)
    # 2) claude.ai upload zip (Settings > Capabilities > Skills): zip containing the folder
    _zip_dir(folder, out / f"{name}-claude-ai.zip", name)
    # 3) Claude Code plugin + single-plugin marketplace
    plugin_root = out / "plugin-marketplace"
    plugin = plugin_root / "plugins" / name
    _copy_tree(skill_dir, plugin / "skills" / name)
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": name, "description": desc[:300], "version": version, "author": {"name": author}}, indent=2) + "\n", encoding="utf-8")
    (plugin_root / ".claude-plugin").mkdir(parents=True)
    (plugin_root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(
        {"name": f"{name}-marketplace", "owner": {"name": author},
         "plugins": [{"name": name, "source": f"./plugins/{name}", "description": desc[:300], "version": version}]},
        indent=2) + "\n", encoding="utf-8")
    # 4) full release zip + manifest
    release = out.parent / f"{name}-{version}.zip"
    _zip_dir(out, release, f"{name}-{version}")
    files = sorted(p for p in out.rglob("*") if p.is_file())
    manifest = {"name": name, "version": version, "author": author,
                "artifacts": {p.relative_to(out).as_posix(): sha256(p) for p in files},
                "release_zip": release.name, "release_sha256": sha256(release)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------- cli
def _print_lint(res):
    for x in res["findings"]:
        print(f"[{x['level'].upper():5}] {x['code']} {x['message']}")
    e = sum(x["level"] == "error" for x in res["findings"])
    w = sum(x["level"] == "warn" for x in res["findings"])
    print(f"\n{'PASS' if res['ok'] else 'FAIL'}: {e} error(s), {w} warning(s)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skillship", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("lint"); a.add_argument("skill_dir"); a.add_argument("--json", action="store_true")
    t = sub.add_parser("triggers"); t.add_argument("skill_dir"); t.add_argument("--table"); t.add_argument("--threshold", type=float, default=0.25); t.add_argument("--json", action="store_true")
    b = sub.add_parser("build"); b.add_argument("skill_dir"); b.add_argument("--out", default="dist"); b.add_argument("--version", default="1.0.0"); b.add_argument("--author", default=os.environ.get("SKILLSHIP_AUTHOR", "Unknown"))
    args = ap.parse_args(argv)
    d = Path(args.skill_dir).resolve()
    if args.cmd == "lint":
        res = lint(d)
        print(json.dumps(res, indent=2)) if args.json else _print_lint(res)
        return 0 if res["ok"] else 1
    if args.cmd == "triggers":
        r = trigger_check(d, Path(args.table) if args.table else None, args.threshold)
        if args.json:
            print(json.dumps(r, indent=2))
        else:
            for row in r["rows"]:
                mark = "ok " if row["pass"] else "BAD"
                exp = "fire" if row["should_trigger"] else "skip"
                hint = "" if row["pass"] else f"  missing: {', '.join(row['missing_terms'])}"
                print(f"{mark} expect={exp} score={row['score']:.2f}  {row['query'][:70]}{hint}")
            print(f"\n{r['passed']}/{r['total']} cases match (heuristic, threshold {r['threshold']})")
        return 0 if r["passed"] == r["total"] else 1
    m = build(d, Path(args.out).resolve(), args.version, args.author)
    print(json.dumps({k: m[k] for k in ("name", "version", "release_zip", "release_sha256")}, indent=2))
    print(f"{len(m['artifacts'])} artifact files written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
