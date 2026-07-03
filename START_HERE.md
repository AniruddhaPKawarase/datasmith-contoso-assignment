# HOW TO START / RESUME DEVELOPMENT

## When You're Ready to Begin (or Resume), Give Claude This Prompt:

---

```
Read these files in order and start development from the next incomplete phase:

1. c:/Users/ANIRUDDHA ASUS/Downloads/Myself/Mtech-4th-sem-PROJECT/PROJECT_DECISIONS_AND_CLARIFICATIONS.md
2. c:/Users/ANIRUDDHA ASUS/Downloads/Myself/Mtech-4th-sem-PROJECT/DEVELOPMENT_ROADMAP.md
3. c:/Users/ANIRUDDHA ASUS/Downloads/Myself/Mtech-4th-sem-PROJECT/OPTION_2_ELEVATED_RESEARCH.md

Start development from the first incomplete phase. Follow the roadmap strictly. Use parallel agents for independent tasks. Apply the multi-agent review process (3-attempt backpropagation) after each phase. Track progress by updating checkboxes in DEVELOPMENT_ROADMAP.md. If limit is about to hit, save the exact resume point.
```

---

## What Each File Contains

| # | File | What Claude Learns From It |
|---|------|---------------------------|
| 1 | `PROJECT_DECISIONS_AND_CLARIFICATIONS.md` | Your decisions: stack, scope, timeline, LLM strategy, all 8 dimensions, acceptance criteria |
| 2 | `DEVELOPMENT_ROADMAP.md` | 10-phase plan with every task, deadline, test requirement, and resume point |
| 3 | `OPTION_2_ELEVATED_RESEARCH.md` | Architecture details, research papers, datasets, open-source tools, novel contributions |

## Tips

- **File 1 is most important** -- it has all your decisions so Claude doesn't re-ask questions
- **File 2 tells Claude exactly what to build next** -- it will find the first `[ ]` checkbox and start there
- **File 3 is reference** -- Claude uses it for architecture decisions and paper references
- Claude's memory system also stores your profile and project status, so it will remember context across sessions
