from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_TEXT_LENGTH = 50_000


class RewriteMode(str, Enum):
    PARAPHRASE = "paraphrase"
    ACADEMIC = "academic"
    PROFESSIONAL = "professional"
    SIMPLE = "simple"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    EXPAND = "expand"
    GRAMMAR = "grammar"
    IMPROVE = "improve"
    SIMPLIFY = "simplify"
    CREATIVE = "creative"
    PERSUASIVE = "persuasive"


class RewriteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    mode: RewriteMode = RewriteMode.PARAPHRASE

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must contain at least one non-whitespace character.")
        return value


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    rewritten_text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("original_text", "rewritten_text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must contain at least one non-whitespace character.")
        return value


class TextMetrics(BaseModel):
    word_count: int
    sentence_count: int
    average_sentence_length: float
    readability: float | None
    readability_label: str | None
    quality_score: int
    quality_score_basis: str


class RewriteResponse(BaseModel):
    original_text: str
    enhanced_text: str
    rewritten_text: str
    mode: str
    canonical_mode: str
    word_count_before: int
    word_count_after: int
    quality_score: int
    readability: float | None
    readability_label: str | None
    changes: list[str]
    processing_time: float
    status: str
    engine: str


class EvaluationResponse(BaseModel):
    original_text: str
    rewritten_text: str
    word_count: int
    sentence_count: int
    average_sentence_length: float
    readability: float | None
    readability_label: str | None
    quality_score: int
    quality_score_basis: str
    original_metrics: TextMetrics
    rewritten_metrics: TextMetrics
    metrics: dict[str, Any]
    status: str


class HistoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
    original_text: str
    enhanced_text: str
    rewritten_text: str
    mode: str
    canonical_mode: str
    word_count_before: int
    word_count_after: int
    quality_score: int
    readability: float | None
    readability_label: str | None
    metrics: dict[str, Any]


class HistoryDeleteResponse(BaseModel):
    deleted_count: int
    status: str
