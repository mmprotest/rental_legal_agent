"""Placeholder agent registry for the multi-agent workflow.

The production system will orchestrate LangGraph nodes for intake, retrieval,
reasoning, drafting, QA, and scheduling. During the planning phase the registry
captures configuration metadata so the rest of the codebase can reference agent
identifiers without hard-coding prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AgentConfig:
    """Minimal description of an agent participant."""

    name: str
    purpose: str
    temperature: float


class AgentRegistry:
    """Mutable collection of agent configurations."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentConfig] = {}

    def register(self, key: str, config: AgentConfig) -> None:
        self._agents[key] = config

    def get(self, key: str) -> AgentConfig:
        return self._agents[key]

    def all(self) -> Dict[str, AgentConfig]:
        return dict(self._agents)


registry = AgentRegistry()
registry.register(
    "intake",
    AgentConfig(
        name="Intake & Issue Classifier",
        purpose="Collect renter facts and categorise the matter.",
        temperature=0.2,
    ),
)
registry.register(
    "law_retriever",
    AgentConfig(
        name="Law Retriever",
        purpose="Fetch relevant Consumer Affairs Victoria and VCAT passages.",
        temperature=0.2,
    ),
)
registry.register(
    "reasoner",
    AgentConfig(
        name="Reasoner",
        purpose="Explain rights, timelines, and actions in plain English.",
        temperature=0.2,
    ),
)
registry.register(
    "drafter",
    AgentConfig(
        name="Letter Drafter",
        purpose="Generate letters and notices with statutory references.",
        temperature=0.0,
    ),
)
registry.register(
    "qa",
    AgentConfig(
        name="QA & Compliance",
        purpose="Validate citations, tone, and missing information before send.",
        temperature=0.0,
    ),
)
registry.register(
    "scheduler",
    AgentConfig(
        name="Deadline Scheduler",
        purpose="Maintain reminders and escalation triggers for the renter.",
        temperature=0.0,
    ),
)

