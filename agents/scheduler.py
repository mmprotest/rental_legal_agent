"""Deadline scheduling helper used by the in-memory store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

from api.models.schemas import CaseCategory, ReasoningStep


@dataclass
class SchedulerResult:
    deadlines: List[ReasoningStep]


class SchedulerAgent:
    """Derive default deadlines for known case categories."""

    def derive(self, category: CaseCategory) -> SchedulerResult:
        today = date.today()
        deadlines: List[ReasoningStep] = []
        if category == CaseCategory.REPAIRS_NONURGENT:
            deadlines.append(
                ReasoningStep(
                    title="Non-urgent repair follow up",
                    description="If the repair isn't complete within 14 days escalate to RDRV.",
                    due_date=today + timedelta(days=14),
                )
            )
        if category == CaseCategory.REPAIRS_URGENT:
            deadlines.append(
                ReasoningStep(
                    title="Urgent repair follow up",
                    description="Check within 24 hours that the rental provider has organised urgent attendance.",
                    due_date=today + timedelta(days=1),
                )
            )
            deadlines.append(
                ReasoningStep(
                    title="Reimbursement due",
                    description="Ensure reimbursement is paid within 7 days for emergency repairs.",
                    due_date=today + timedelta(days=7),
                )
            )
        return SchedulerResult(deadlines=deadlines)
