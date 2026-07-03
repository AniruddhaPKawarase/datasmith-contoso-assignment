# Mid-Sem Demo — Recording Instructions (Backup Video)

**Purpose:** produce a 3-minute backup MP4 in case the live demo fails on viva day.
The video plays *only* if Docker / API / network fails during the live run; otherwise
it is unused. But it must exist before 2026-06-16.

---

## 1.  What to record

A single uninterrupted screen capture of `scripts/midsem_demo.py` running
end-to-end, with audio narration aligned to `MIDSEM_DEMO_NARRATION.md`.

Three demo sections:

| # | Demo | Wall-clock | Key thing on screen |
|---|---|---|---|
| D1 | Cross-domain + temporal + RBAC | ~5 sec exec, ~45 sec narration | The composed CTE SQL with per-CTE `company_id IN (1)` |
| D2 | Multi-turn dialogue (3 turns) | ~15 sec exec, ~75 sec narration | The `[domains] finance, demand ← inherited from T1` line on T2 / T3 |
| D3 | Ambiguity refusal | ~2 sec exec, ~30 sec narration | The `[panel] By 'lead time', do you mean ...` clarification |

Plus a 10-sec opener and 15-sec closer (token table + cost).

**Total runtime target: ~3:00.** Hard cap: 3:30.

---

## 2.  Pre-recording checklist (5 min)

```powershell
cd "C:\Users\ANIRUDDHA ASUS\Downloads\Myself\Mtech-4th-sem-PROJECT\Project_dev"

# 1. Docker stack healthy
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr scm-
# Expect: scm-postgres, scm-redis, scm-odoo all "Up ... (healthy)"

# 2. 498-table Odoo schema loaded
docker exec scm-postgres psql -U odoo -d odoo -tAc `
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
# Expect: 498

# 3. API keys present
$env:ANTHROPIC_API_KEY.Length    # > 0
$env:OPENAI_API_KEY.Length        # > 0

# 4. Demo script dry-run (do NOT record this — just sanity check)
.\.venv\Scripts\python.exe scripts\midsem_demo.py
# Expect: all 3 demos run, EXPLAIN OK, total cost ~$0.04
```

If any check fails, **stop** and fix before recording. A retake is cheap; a
visible error on the recording is not.

---

## 3.  Recording setup

| Setting | Value |
|---|---|
| Capture tool | OBS Studio (free) or Windows Game Bar (Win+Alt+R) |
| Resolution | 1920×1080 minimum, 1280×720 acceptable |
| Frame rate | 30 fps |
| Format | MP4 (H.264) |
| Audio | Single channel, 44.1 kHz, push-to-talk mic |
| Terminal font | Cascadia Code 16pt minimum (panel must read it on a projector) |
| Terminal theme | Dark background, light text (high contrast) |
| Other apps closed | Yes — no notifications, no browser tabs, no Slack |

Window arrangement: terminal full-screen. No IDE, no editor.

---

## 4.  Recording sequence

1. Start the screen capture.
2. Wait 2 seconds (silent dead air — for editing).
3. Speak the opening line aloud:
   > *"I'll show you three queries that exercise the central capabilities
   > of the system — cross-domain composition, multi-turn dialogue, and
   > ambiguity handling. Total runtime is about three minutes."*
4. Type and run:
   ```powershell
   .\.venv\Scripts\python.exe scripts\midsem_demo.py
   ```
5. As D1 prints, speak the D1 narration from `MIDSEM_DEMO_NARRATION.md §Demo 1`.
6. As D2 prints (3 turns), speak the D2 narration — pace yourself to align with
   each turn printing.
7. As D3 prints, speak the D3 narration.
8. After the TOKEN USAGE table prints, speak the closing line:
   > *"Four cents for the whole demo. The transcript is saved to
   > `docs/viva/MIDSEM_DEMO_LOG_<timestamp>.txt`."*
9. Wait 2 seconds (silent dead air — for editing).
10. Stop the screen capture.

---

## 5.  Post-recording

| Step | Action |
|---|---|
| 1. Save raw file | `docs/viva/MIDSEM_DEMO_RAW_<timestamp>.mp4` |
| 2. Trim heading/tail dead air | Use Clipchamp (Windows built-in) or DaVinci Resolve |
| 3. Sanity-check audio levels | -12 to -6 dB peaks; no clipping |
| 4. Verify total runtime | ≤ 3:30; ideally 3:00 ±15 sec |
| 5. Final filename | `docs/viva/MIDSEM_DEMO_BACKUP.mp4` |
| 6. Put a copy on a USB stick | One USB stays in your bag; one in your pocket |

**Do NOT post to YouTube** — keep the backup local. The video shows the live
Postgres instance, query latencies, and the API spend; that's internal data.

---

## 6.  When to play the backup (decision tree)

```
Live demo attempt started
       │
       ├── Docker container missing  → backup video
       ├── Postgres unreachable      → backup video
       ├── API rate-limit hit        → wait 10s, retry once → backup video
       ├── EXPLAIN fails on 1 query  → keep going (narrate as documented)
       └── Demo runs end-to-end      → no backup needed
```

If the backup plays, say:
> *"For time, let me show the recorded run instead. The system you'll see is
> the same one running on this machine — I prepared this in case of network
> issues."*

Don't apologise. Don't troubleshoot live. The video is the demo.

---

## 7.  What the clean demo transcript looks like

The transcript file written by the demo script lives at:

```
docs/viva/MIDSEM_DEMO_LOG_<timestamp>.txt
```

It contains the exact stdout of the demo run — the SQL, the EXPLAIN OK
lines, the token-usage table. Keep at least the most recent transcript
committed to git so the panel can see *historic* runs (in case they ask
"can we see one from yesterday").

---

*Document version 1.0  ·  Generated 2026-05-27  ·  Author: Aniruddha Prakash Kawarase*
