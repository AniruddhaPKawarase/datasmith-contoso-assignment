"""Composer — merges sub-queries from domain agents into one executable SQL.

The deterministic Composer (no LLM) is the default path:
* 1 fragment  → pass-through with a wrapper SELECT.
* 2+ fragments → wrap each in a CTE; merge as a CROSS JOIN over single-
  row CTEs when no shared join key is detected, otherwise INNER JOIN on
  the discovered key.

For Phase 5 we ship the deterministic path; an LLM-driven Composer is a
future enhancement when the deterministic logic isn't enough.
"""

from app.composer.composer import Composer, ComposerResult

__all__ = ["Composer", "ComposerResult"]
