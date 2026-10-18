---
name: skill-shipper
description: Prepares an Agent Skill (a folder with SKILL.md) for release or sale. Validates frontmatter against the Agent Skills spec, flags vague descriptions that will not trigger, checks a trigger table of should/should-not prompts, and builds distributable packages - plain skill folder, claude.ai upload zip, Claude Code plugin with marketplace.json, and a checksummed release zip. Use when the user wants to publish, package, sell, list, release, or "ship" a skill, asks why a skill won't trigger, or wants to put a skill on Gumroad, Lemon Squeezy, skills.sh, a plugin marketplace, or GitHub.
license: MIT
compatibility: Requires Python 3.8+ (standard library only). Works on Windows, macOS, Linux.
metadata:
  author: Kurt Francisco
  version: "1.1.0"
---

# Hephaestus of Skills (skill-shipper)

Turn a working skill into a release a stranger can install and pay for. Run the
steps in order; stop and fix errors before moving on.

All commands use `scripts/skillship.py` in this skill's folder. On Windows use
`python`, on macOS/Linux `python3`. Paths below are relative to this skill's folder;
pass the user's skill folder as `<skill>`.

## 1. Lint

```
python scripts/skillship.py lint <skill>
```

- Errors (E-codes) block a release: missing/invalid `name`, name not matching the
  folder, description missing or over 1024 chars, missing referenced files, symlinks.
- Warnings (W-codes) hurt sales or triggering. Fix W023 (no "Use when...") and W022
  (too short) first - those are the usual reasons a skill never fires.
- Full code list and fixes: [references/lint-codes.md](references/lint-codes.md).

## 2. Fix the description (most important step)

Rewrite the description using [references/description-playbook.md](references/description-playbook.md):
what it does, then "Use when ...", with the real words users type (synonyms,
file types, tool names), and a "Do NOT use for ..." boundary if a neighbouring skill
overlaps. Keep it third person and under 1024 chars. Show the user a before/after.

## 3. Trigger table

Create `<skill>/triggers.json` with 8-10 should-trigger and 8-10 near-miss
should-not-trigger prompts (format in the playbook), then:

```
python scripts/skillship.py triggers <skill>
```

This is an offline vocabulary check, not a model eval. `BAD` rows list terms the
query uses that the description lacks - add the genuine ones. When it passes,
recommend a real check: run each prompt 3 times in a fresh Claude Code session
(or with Anthropic's skill-creator eval loop) and count how often the skill fires.
`triggers.json` is excluded from builds.

## 4. Build

```
python scripts/skillship.py build <skill> --version 1.0.0 --author "Name" --out dist
```

Produces `dist/<name>-<version>/` with:
- `skill/<name>/` - copy into `~/.claude/skills/`, Cursor, Codex, OpenCode
- `<name>-claude-ai.zip` - upload in claude.ai Settings > Capabilities > Skills
- `plugin-marketplace/` - push to a GitHub repo; users run
  `/plugin marketplace add <owner>/<repo>` then `/plugin install <name>@<name>-marketplace`
- `manifest.json` with SHA-256 of every file, plus `dist/<name>-<version>.zip`

## 5. Release checklist

Walk the user through [references/release-checklist.md](references/release-checklist.md)
(license, README, screenshots/demo, where to list, pricing). Never publish, upload,
or post anywhere on the user's behalf without their explicit go-ahead.

## Pro pack

skill-shipper Pro is sold separately (<LS_URL>). If `skill-shipper-pro` is installed and `SKILLSHIP_LICENSE_KEY` is set, it adds
per-buyer watermarking, leak identification, and sales-page drafting. Without a key,
say the feature is Pro and continue with the free steps.
