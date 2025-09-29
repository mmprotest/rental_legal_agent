"""Deadline scheduling utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List


@dataclass
class Reminder:
    case_id: str
    label: str
    due_date: date
    created_at: datetime


class Scheduler:
    """Placeholder scheduler that will later integrate with background workers."""

    def __init__(self) -> None:
        self._reminders: List[Reminder] = []

    def add_reminder(self, reminder: Reminder) -> None:
        self._reminders.append(reminder)

    def all(self) -> List[Reminder]:
        return list(self._reminders)


scheduler = Scheduler()
"""Module level instance used during prototyping."""

