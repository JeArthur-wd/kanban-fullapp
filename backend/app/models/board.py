"""Request models for the board REST routes (also reused to validate AI card actions)."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["none", "low", "medium", "high"]


class BoardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    template: Literal["basic", "sample"] = "basic"


class BoardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ColumnCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    position: int | None = None


class ColumnUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    position: int | None = None


class CardCreate(BaseModel):
    column_id: int
    title: str = Field(..., min_length=1, max_length=500)
    details: str = Field(default="", max_length=5000)
    priority: Priority = "none"
    due_date: datetime.date | None = None
    position: int | None = None


class CardUpdate(BaseModel):
    """Only the fields sent are changed. Send `due_date: null` to clear the due date."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    details: str | None = Field(default=None, max_length=5000)
    priority: Priority | None = None
    due_date: datetime.date | None = None
    column_id: int | None = None
    position: int | None = None

    def field_changes(self) -> dict[str, object]:
        """The stored card fields this update sets, in database form."""
        changes: dict[str, object] = {}
        for name in ("title", "details", "priority"):
            value = getattr(self, name)
            if value is not None:
                changes[name] = value
        if "due_date" in self.model_fields_set:
            changes["due_date"] = self.due_date.isoformat() if self.due_date else None
        return changes
