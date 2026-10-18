# Hephaestus of Skills

*Formerly **skill-shipper**. The repo is now `fpavia111-creator/hephaestus`. The skill itself keeps its name `skill-shipper` (so `/skill-shipper`, existing installs and `skillship.py` keep working), and existing skill-shipper Pro keys keep working.*

**Ship an Agent Skill so a stranger can install it, and pay for it.**
Hephaestus of Skills (`skill-shipper`) is an Agent Skill (SKILL.md) with a small Python CLI, standard library only.
It **lints** a skill against the Agent Skills spec, **flags descriptions that won't trigger**,
runs an offline **trigger-table check**, and **builds** every format people install from:
a plain skill folder, a claude.ai upload zip, a Claude Code plugin with `marketplace.json`, and a
checksummed release zip. **Hephaestus Pro** (formerly skill-shipper Pro, $11 one-time, [buy here](https://buy.stripe.com/4gM28t0rf1kSb0v9WN5AQ02)) adds per-buyer watermarking, leak tracing,
and sales-page drafts for people selling skills.

Runs on Windows, macOS, and Linux with Python 3.8+. No dependencies, no symlinks, no network calls.

```
free/skill-shipper/        MIT. The skill: SKILL.md, scripts/skillship.py, references/
examples/invoice-chaser/   A deliberately weak skill + triggers.json for the demo
tests/                     unittest suite
demo.py                    End-to-end demo in a temp folder
install.ps1 / install.sh   Copy-based installers
```

## Install

Quick install with skills.sh: `npx skills add fpavia111-creator/hephaestus`

Repo: https://github.com/fpavia111-creator/hephaestus

### Windows (PowerShell)
```powershell
cd path\to\hephaestus
python -m unittest discover -s tests        # optional: run the tests
.\install.ps1                               # Claude Code: $HOME\.claude\skills\skill-shipper
.\install.ps1 -Target cursor                # Cursor:      $HOME\.cursor\skills
.\install.ps1 -Target project               # this repo:   .\.claude\skills
```
If script execution is blocked, run `Set-ExecutionPolicy -Scope Process Bypass` first. Manual alternative:
`Copy-Item -Recurse free\skill-shipper $HOME\.claude\skills\`.

### macOS / Linux
```bash
./install.sh claude        # or cursor | codex | project
```

### Per tool
| Tool | How |
|---|---|
| Claude Code | Copy `free/skill-shipper` to `~/.claude/skills/` (user) or `.claude/skills/` (project). Restart the session. Ask "package my X skill for release", or run `/skill-shipper`. |
| claude.ai (Pro/Max/Team/Enterprise) | Zip the `skill-shipper` folder (or run `skillship build` on it) and upload the `-claude-ai.zip` under Settings > Capabilities > Skills. The scripts need code execution turned on. |
| Cursor | Copy it into `~/.cursor/skills/` (or the project `.cursor/skills/`). Cursor reads SKILL.md skills. |
| Codex CLI / OpenCode / other SKILL.md agents | Copy the folder into the agent's skills directory. |
| Any agent, or no agent | Use the CLI directly: `python free/skill-shipper/scripts/skillship.py lint|triggers|build <skill>` |

## CLI
```
python scripts/skillship.py lint     <skill> [--json]
python scripts/skillship.py triggers <skill> [--table triggers.json] [--threshold 0.25]
python scripts/skillship.py build    <skill> --version 1.0.0 --author "Name" --out dist
```
Exit codes: 0 means pass, 1 means lint errors or trigger mismatches, so you can use it in CI.

## Limitations
- `triggers` is a keyword-overlap heuristic, not a model eval. Use it to find vocabulary gaps, then confirm in Claude Code or with skill-creator.
- The frontmatter parser handles the YAML subset skills use (scalars, quotes, `>`/`|` blocks, one-level maps). It does not handle lists or anchors.
- Plugin and marketplace JSON follow the documented Claude Code layout. Run `/plugin marketplace add` against a real repo once before publishing.
- `install.ps1` was written for Windows but not executed in CI (no PowerShell on the build box).
- No MCP server: the CLI covers everything, so one was left out deliberately.

## Pro
Hephaestus Pro (formerly skill-shipper Pro: per-buyer watermarking, leak identification, sales-page drafts) is sold separately for **$11 one-time**.

**[Buy Hephaestus Pro: $11 one-time →](https://buy.stripe.com/4gM28t0rf1kSb0v9WN5AQ02)**

Payment is handled by Stripe; your license key arrives by email. Pro is not part of this repository and is not covered by the MIT license.
