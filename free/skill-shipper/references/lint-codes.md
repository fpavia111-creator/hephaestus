# Lint codes

| Code | Level | Meaning | Fix |
|---|---|---|---|
| E001 | error | No `SKILL.md` | Exact filename, uppercase |
| E002 | error | Frontmatter missing/unclosed/malformed | `---` must be line 1 and close the block |
| E010/E011 | error | `name` missing or invalid | 1-64 chars, `a-z0-9`, single hyphens, no leading/trailing hyphen |
| E012 | error | `name` != folder name | Rename one of them |
| E020/E021 | error | `description` missing or > 1024 chars | See description playbook |
| E030 | error | `compatibility` > 500 chars | Shorten |
| E031 | error | `metadata` not a map | Use `key: value` lines indented under `metadata:` |
| E051 | error | Body references a file that doesn't exist | Add it or fix the path |
| E060 | error | Symlink in skill | Copy the real file (symlinks break zips and Windows) |
| W022 | warn | Description < 80 chars | Add what + when + keywords |
| W023 | warn | No "when to use" phrase | Add "Use when ..." |
| W024 | warn | First-person description | Third person: "Generates..." |
| W025 | warn | `<` `>` in description | Remove angle brackets |
| W032 | warn | Unknown frontmatter field | Claude Code silently ignores unknown keys - check spelling |
| W040 | warn | Body > 500 lines | Move detail into `references/` |
| W041 | warn | Body very short | Add steps, examples, edge cases |
| W050 | warn | Backslash path | Use `/` |
| W052 | warn | Absolute user path | Use paths relative to the skill folder |
| W061 | warn | `.env`/`.DS_Store`/`Thumbs.db` present | Excluded from builds; remove secrets anyway |
| W070 | warn | No license | Add `license:` or a LICENSE file |

Sources: https://agentskills.io/specification and https://code.claude.com/docs/en/skills
