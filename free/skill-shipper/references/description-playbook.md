# Description playbook

The description is the only text the agent sees before deciding to load a skill.

Template:

> [Verb]s [object] [doing X, Y, Z]. Use when the user [situations], mentions
> [synonyms / file types / tool names], or asks to [phrasings]. Do NOT use for
> [neighbouring task] (use [other skill]).

Rules
1. Lead with the capability, then "Use when". Key use case first (Claude Code truncates
   long listings).
2. Use the user's vocabulary, not yours: "changelog" and "release notes", "invoice" and "bill".
3. Third person. No "I can".
4. Name concrete artifacts: file types, services, commands.
5. Add a boundary when another skill is close.
6. Simple one-step asks ("read this PDF") may never trigger any skill; that's expected.

## triggers.json format

```json
[
  {"query": "package my pdf-tools skill so I can sell it on gumroad", "should_trigger": true},
  {"query": "write a python script that zips a folder", "should_trigger": false}
]
```

Write realistic, specific prompts, including near-misses that share words but need a
different skill. Re-run after every description edit; triggering regresses silently.

References: https://github.com/agentskills/agentskills/blob/main/docs/skill-creation/optimizing-descriptions.mdx ,
https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
