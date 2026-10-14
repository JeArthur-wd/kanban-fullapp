"""Request models for the board REST routes (also reused to validate AI card actions)."""

from pydantic import BaseModel, Field


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
    position: int | None = None


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    details: str | None = Field(default=None, max_length=5000)
    column_id: int | None = None
    position: int | None = None
