# OUTLINE VIVA — 12-DAY PREP PLAN

**Viva date:** 2026-05-26  ·  **T-minus today (2026-05-14):** 12 days
**Student:** Aniruddha Prakash Kawarase  ·  **BITS ID:** 2024AA05175
**Project:** Domain-Aware Multi-Agent NL-to-SQL for Enterprise Supply Chain Intelligence

> **The setup you walk in with:** 7 of 10 roadmap phases complete; a live system that produces validated PostgreSQL against a 498-table Odoo schema; 210 unit tests at 87 % coverage; ~$0.10 of LLM spend across all dev so far. Your goal for these 12 days is **fluency**, not more code. The panel will judge you on framing, novelty, and command of the literature — every one of those is already in your favour. Don't crowd them out with last-minute coding.

---

## How to use this plan

Each day has:
- **One primary outcome** — finish this before moving on.
- **Bounded time** — 2 to 3 hours of focused work. Skip if life intervenes; do not double-up the next day.
- **An end-of-day check** — one sentence you should be able to write or say out loud.

The plan is front-loaded for content mastery, then mid-loaded for repetition, then back-loaded for taper + recovery. Days 11 + 12 are deliberately light.

---

## Day 1 — Today (Wed 14 May)

**Primary outcome.** Read this 12-day plan, [VIVA_PREP_OUTLINE.md](VIVA_PREP_OUTLINE.md), [VIVA_DEMO_SCRIPT.md](VIVA_DEMO_SCRIPT.md), [VIVA_WHITEBOARD.md](VIVA_WHITEBOARD.md) end-to-end once. Don't memorise yet — just absorb the shape.

**Bounded time.** 90 min.

**End-of-day check.** Write one sentence: *"The novelty of my dissertation is …"* (you should already be able to answer this in under 30 s after one read-through).

---

## Day 2 — Thu 15 May  ·  The 30-second pitch + the gap

**Primary outcome.** Memorise the 30-second elevator pitch in [VIVA_PREP_OUTLINE.md §1](VIVA_PREP_OUTLINE.md). Recite it out loud 10 times. The last 3 reps should be done while you're physically moving (walking, doing dishes) — that locks it in.

**Drill.** Section 4 of VIVA_PREP_OUTLINE — the research gap table. Be able to recite, from memory, the four columns: *what exists, what's missing, the four hard numbers (10.1 % Spider 2.0, 39.1 % BIRD-Ent, 498 Odoo tables, no SCM benchmark).*

**Bounded time.** 2 h.

**End-of-day check.** Stand in front of a mirror, deliver the 30-sec pitch + the gap, time yourself. **Target: under 90 s combined.**

---

## Day 3 — Fri 16 May  ·  The 5-layer architecture

**Primary outcome.** Whiteboard practice. Draw the 5-layer architecture from [VIVA_WHITEBOARD.md §1](VIVA_WHITEBOARD.md) **from memory** five times on a fresh page each time.

**Why this matters.** This is the *single most likely viva moment*: the examiner will say *"draw me your system."* You want to start drawing within 5 seconds, finish in under 90 s, and narrate as you go.

**Bounded time.** 2 h.

**End-of-day check.** Record yourself (phone camera) drawing + narrating once. Watch it back. If you said "uhh" more than 3 times, do one more rep tomorrow morning.

---

## Day 4 — Sat 17 May  ·  Demo dry-run

**Primary outcome.** Run the live demo end-to-end **without help**. Follow [VIVA_DEMO_SCRIPT.md](VIVA_DEMO_SCRIPT.md) line-by-line. Open the laptop fresh, start Docker, run `scripts/smoke_phase7.py`, narrate each turn.

**Bounded time.** 2 h (including a recording).

**Recording is mandatory.** Phone propped on a book is fine. This is your **backup video** for viva day — if Docker dies live, you'll play this instead. Save as `Project_dev/docs/viva_demo_2026_05_17.mp4` (or wherever; just don't lose it).

**End-of-day check.** Watch the recording at 1.5× speed. Is everything that happens narratable? If yes, you're done. If no, identify the dark spot and re-record just that section.

---

## Day 5 — Sun 18 May  ·  Q1–Q10 drill (Problem + Novelty + Architecture)

**Primary outcome.** Drill questions Q1 to Q10 from [VIVA_PREP_OUTLINE.md §12](VIVA_PREP_OUTLINE.md). Out loud. Each in under 60 seconds.

**How to drill.** Tear a piece of paper into 10 strips, one question per strip, shuffle, and answer cold. If you fumble any, set that strip aside and re-do it at the end. Repeat until all 10 are clean.

**Bounded time.** 2.5 h.

**End-of-day check.** *Q4 ("How is this different from MAC-SQL?")* and *Q5 ("Isn't this just routing?")* are the high-leverage ones. Be able to answer those two in under 45 s each.

---

## Day 6 — Mon 19 May  ·  Q11–Q20 drill (Evaluation + Risks + Personal)

**Primary outcome.** Same drill, Q11 to Q20.

**High-leverage questions today:**
- *Q13 — "What's your target accuracy?"* Have specific numbers ready: ≥85 % EX on Spider, within 5 pp of CHASE-SQL on BIRD, ≥10 pp lift on SCM-SQL Levels 3–6.
- *Q15 — "What's your biggest risk?"* Composer reliability at Level 4+ → Phase 5 already proved it works; mitigation is the narrow midterm slice.
- *Q18 — "Why this project not Option 1?"* The single most likely *personal* question. Practise this until it sounds unrehearsed.

**Bounded time.** 2.5 h.

**End-of-day check.** You can answer all 20 questions out of order without looking.

---

## Day 7 — Tue 20 May  ·  Literature deep-dive day 1

**Primary outcome.** Read (or skim, if pressed) abstracts + section 1 (intro) + section 5 (conclusions) of the top 6 papers in [VIVA_PREP_OUTLINE.md §13](VIVA_PREP_OUTLINE.md):

1. MAC-SQL (Wang et al., COLING 2025) — the baseline you beat
2. MARS-SQL (Chen et al., Nov 2025) — RL feedback loop you borrow
3. CHASE-SQL (Pourreza et al., ICLR 2025) — candidate selection
4. Spider 2.0 (Lei et al., ICLR 2025 Oral) — the 10.1 % number
5. Floratou et al. (CIDR 2024) — "NL2SQL is NOT solved"
6. AmbiSQL (Liu et al., 2025) — ambiguity resolution

For each, write **one sentence answering**: *"How is my system different from this paper?"* Save these in a single text file or page in your notebook.

**Bounded time.** 3 h.

**End-of-day check.** You can name each paper's *single most important finding* without looking, and what makes your work distinct.

---

## Day 8 — Wed 21 May  ·  Literature deep-dive day 2 + supervisor's remark

**Primary outcome.** Same drill for papers 7–10 (NL2SQL Survey, Klabe et al. agentic LLMs in SCM, BIRD, Qwen 2.5-Coder report). These are lighter — abstract + intro only is fine.

**Then:** read your supervisor's remark from VIVA_PREP_OUTLINE §14 out loud. If you're pushed in a corner during the viva, quoting the supervisor's exact phrase ("the research gap is genuine and well argued") is fair game.

**Bounded time.** 2 h.

**End-of-day check.** You have a mental map: *"Which paper do I cite for which claim in my methodology?"*

---

## Day 9 — Thu 22 May  ·  Full mock viva (recorded)

**Primary outcome.** Find a friend / family member / fellow MTech candidate. Hand them VIVA_PREP_OUTLINE §12 and have them quiz you for 30 minutes. Record audio (your phone is fine — Voice Memo / Recorder app).

**Their brief.** Pick 8 questions at random from §12. Mix in 2 "trap" questions ("what if I told you GPT-4o now hits 50 % on Spider 2.0?") — they don't need to be sophisticated; the goal is to practise unflappable composure under unexpected pressure.

**Bounded time.** 1 h prep + 1 h mock + 1 h listening back = 3 h.

**End-of-day check.** Note 2–3 things you'd improve and drill them tomorrow. Don't try to fix everything; pick the worst 2.

---

## Day 10 — Fri 23 May  ·  Targeted fixes + 6 query-level examples

**Primary outcome.** Drill the **two worst things from the mock**. Be honest. If your hands shook on Q5, do Q5 ten more times. If you blanked on Spider 2.0's number, write 10.1 % on a sticky note and stare at it for an hour.

**Then:** make sure you can give one concrete query example per complexity level (1–6) from VIVA_PREP_OUTLINE §8. These come up in *every* NL-to-SQL viva.

**Bounded time.** 2 h.

**End-of-day check.** You feel calmer than yesterday about the worst-mock-question. Calmer, not perfect.

---

## Day 11 — Sat 24 May  ·  Read everything one last time, then stop

**Primary outcome.** Read VIVA_PREP_OUTLINE.md end-to-end once more. Read your abstract docx once. Read VIVA_DEMO_SCRIPT.md once.

**Then:** stop. Go for a walk. Watch something light. Sleep early.

**The hardest discipline of the prep cycle is to *not* over-prepare on day 11.** You're going to retain ~70 % of what you've drilled. Adding another 5 % at the cost of being exhausted on viva day is a bad trade.

**Bounded time.** 90 min reading + 0 min more.

**End-of-day check.** Phone off by 9 PM. Lights out by 10:30.

---

## Day 12 — Sun 25 May (T-1)

**Primary outcome.** **No project work.** Confirm logistics only:

- Verify the time + format (online vs in-person) on the BITS portal.
- Charge laptop. Check Docker is running. Run `scripts/smoke_phase7.py` once to confirm the demo works on the actual machine you'll bring.
- If online: test the screen-share setup (Zoom / Google Meet / whatever BITS uses).
- Have your supervisor's remark + the abstract docx open in tabs you can flip to.
- Print or PDF-bookmark VIVA_PREP_OUTLINE.md §15 ("The Final 10 rapid-fire facts") for the morning of.

**Bounded time.** 30 min logistics + 0 min content.

**Eat well. Sleep early. You're ready.**

---

## Viva day — Mon 26 May

**Pre-viva (30 min before).**
- Re-read [VIVA_PREP_OUTLINE.md §1, §2, §15](VIVA_PREP_OUTLINE.md) only. Nothing else.
- Do not look at any paper. Do not run the demo. Just §1 and §15.

**During the viva.**
- If you blank: pause, breathe, say *"Let me think for a moment"* — silence is a power move, not a weakness.
- If they ask for a number you forgot: estimate aloud and say *"I'd want to verify the exact figure but the order of magnitude is …"* — examiners respect calibrated honesty.
- If they push back: **don't argue**. Say *"That's a fair challenge. My answer is X, but I'd be interested to hear your view."* and then *listen*.

**Post-viva.**
- Whatever happens, you have a working 7-phase system. That's an extraordinary outcome for an outline viva. The result is already locked in by your prep, not by the conversation.

---

## What this plan deliberately omits

- **No more coding.** Phase 8/9/10 work waits.
- **No more reading beyond the 10 papers.** Going wider doesn't help; going deeper on the 10 you cite does.
- **No new slides / visuals.** What you have works.
- **No optimisation of answers you can already give cleanly.** Diminishing returns.

---

## Emergency-fix table

| If, on Day N, you realise X | Then |
|---|---|
| You can't deliver the 30-sec pitch under 30 s | Re-do Day 2 for one more hour; ignore the rest of Day N's plan |
| Docker isn't running on your viva-day laptop | Your video from Day 4 is the answer; that's why we recorded it |
| You hit a question in mock viva you cannot answer | Write it on a sticky note. Drill it 5× across days 10 and 11. Don't panic — the panel will not ask every question |
| You're not sleeping the night before | This plan accounts for that; days 11 + 12 are deliberately low-load |

---

*Generated 2026-05-14. Source artefacts: VIVA_PREP_OUTLINE.md, VIVA_DEMO_SCRIPT.md, VIVA_WHITEBOARD.md, DEVELOPMENT_ROADMAP.md.*
