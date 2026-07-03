"""Multi-turn conversational reasoning (Phase 7).

The components:

- ``ReferenceDetector`` classifies a follow-up query into one of four
  kinds: new_topic, refinement, comparison, follow_up. The classification
  is rule-based + cheap; no LLM call.
- ``ConversationContextBuilder`` turns the active window of ``Turn``
  objects (already maintained by ``ConversationMemory`` from Phase 3)
  into a structured prompt block that each domain agent receives via
  the existing ``context`` kwarg.

Reference resolution itself (pronoun → entity) is *delegated to the
domain agent's LLM*, but the agent is given enough structured prior
context that it can do this reliably:

  - last turn's user query
  - last turn's composed SQL
  - last turn's domains used
  - a one-line summary of older turns (compressed by ``ConversationMemory``)
"""

from app.conversation.builder import ConversationContextBuilder
from app.conversation.references import (
    ReferenceDecision,
    ReferenceDetector,
    ReferenceKind,
)

__all__ = [
    "ConversationContextBuilder",
    "ReferenceDecision",
    "ReferenceDetector",
    "ReferenceKind",
]
