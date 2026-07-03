"""Multi-agent framework.

Contents:
- ``state``         : LangGraph state TypedDict + sub-query record
- ``messages``      : Inter-agent communication protocol (audit-friendly)
- ``memory``        : Multi-turn conversation memory
- ``base``          : ``BaseAgent`` abstract class
- ``router``        : Router/Planner agent (domain classification)
- ``orchestrator``  : LangGraph state machine wiring everything together
"""
from app.agents.base import AgentResult, BaseAgent, StubDomainAgent
from app.agents.compliance import (
    ComplianceContext,
    ComplianceDecision,
    ComplianceProcessor,
)
from app.agents.memory import ConversationMemory, Turn
from app.agents.messages import AgentMessage, MessageKind, MessageLog
from app.agents.orchestrator import Orchestrator
from app.agents.router import RouterAgent, RouterDecision
from app.agents.specialists import (
    FewShot,
    LLMDomainAgent,
    build_specialists,
    extract_sql,
    load_few_shots,
    tables_referenced,
)
from app.agents.state import (
    AgentOutput,
    AgentState,
    OrchestratorLimits,
    SubQuery,
    ValidationIssue,
    fresh_state,
)

__all__ = [
    "AgentMessage",
    "AgentOutput",
    "AgentResult",
    "AgentState",
    "BaseAgent",
    "ComplianceContext",
    "ComplianceDecision",
    "ComplianceProcessor",
    "ConversationMemory",
    "FewShot",
    "LLMDomainAgent",
    "MessageKind",
    "MessageLog",
    "Orchestrator",
    "OrchestratorLimits",
    "RouterAgent",
    "RouterDecision",
    "StubDomainAgent",
    "SubQuery",
    "Turn",
    "ValidationIssue",
    "build_specialists",
    "extract_sql",
    "fresh_state",
    "load_few_shots",
    "tables_referenced",
]
