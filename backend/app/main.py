from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import database, history
from app.quality import count_words, evaluate_text, metrics_for_api
from app.rewriting import ENGINE_NAME, canonical_mode, rewrite_text
from app.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    HistoryDeleteResponse,
    HistoryRecord,
    RewriteRequest,
    RewriteResponse,
)


logger = logging.getLogger("text_rewriter")


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize_database()
    yield


app = FastAPI(
    title="Natural Language Rewriting and Text Enhancement API",
    description=(
        "A local, deterministic, rule-based text rewriter. It does not use or claim "
        "to run a pretrained AI model."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(_: Request, exc: sqlite3.Error) -> JSONResponse:
    logger.exception("SQLite operation failed", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Rewrite history storage is temporarily unavailable."},
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "Natural Language Rewriting and Text Enhancement API",
        "status": "ok",
        "engine": ENGINE_NAME,
        "engine_description": (
            "Deterministic local rule-based rewriting; no pretrained model or paid API "
            "is used."
        ),
        "docs": "/docs",
        "endpoints": [
            "GET /health",
            "POST /api/rewrite",
            "POST /api/evaluate",
            "GET /api/history",
            "GET /api/history/{record_id}",
            "DELETE /api/history",
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    database.check_database()
    return {"status": "ok", "engine": ENGINE_NAME, "storage": "sqlite"}


@app.post("/api/rewrite", response_model=RewriteResponse)
def create_rewrite(request: RewriteRequest) -> RewriteResponse:
    started = time.perf_counter()
    enhanced_text, effective_mode, changes = rewrite_text(request.text, request.mode)
    metrics = evaluate_text(enhanced_text)
    original_count = count_words(request.text)
    saved = history.save_rewrite(
        original_text=request.text,
        enhanced_text=enhanced_text,
        mode=request.mode.value,
        canonical_mode=effective_mode,
        word_count_before=original_count,
        word_count_after=count_words(enhanced_text),
        quality_score=metrics.quality_score,
        readability=metrics.readability,
        readability_label=metrics.readability_label,
        metrics=metrics_for_api(metrics),
    )
    logger.info("Saved rewrite history record %s", saved["id"])
    return RewriteResponse(
        original_text=request.text,
        enhanced_text=enhanced_text,
        rewritten_text=enhanced_text,
        mode=request.mode.value,
        canonical_mode=effective_mode,
        word_count_before=original_count,
        word_count_after=count_words(enhanced_text),
        quality_score=metrics.quality_score,
        readability=metrics.readability,
        readability_label=metrics.readability_label,
        changes=changes,
        processing_time=round(time.perf_counter() - started, 6),
        status="success",
        engine=ENGINE_NAME,
    )


@app.post("/api/evaluate", response_model=EvaluationResponse)
def evaluate(request: EvaluationRequest) -> EvaluationResponse:
    original_metrics = evaluate_text(request.original_text)
    rewritten_metrics = evaluate_text(request.rewritten_text)
    display_metrics = metrics_for_api(rewritten_metrics)
    display_metrics["quality_score_change"] = (
        rewritten_metrics.quality_score - original_metrics.quality_score
    )
    return EvaluationResponse(
        original_text=request.original_text,
        rewritten_text=request.rewritten_text,
        word_count=rewritten_metrics.word_count,
        sentence_count=rewritten_metrics.sentence_count,
        average_sentence_length=rewritten_metrics.average_sentence_length,
        readability=rewritten_metrics.readability,
        readability_label=rewritten_metrics.readability_label,
        quality_score=rewritten_metrics.quality_score,
        quality_score_basis=rewritten_metrics.quality_score_basis,
        original_metrics=original_metrics,
        rewritten_metrics=rewritten_metrics,
        metrics=display_metrics,
        status="success",
    )


@app.get("/api/history", response_model=list[HistoryRecord])
def read_history(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
    return history.list_rewrites(limit=limit)


@app.get("/api/history/{record_id}", response_model=HistoryRecord)
def read_history_record(record_id: int) -> dict[str, Any]:
    record = history.get_rewrite(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Rewrite history record not found.")
    return record


@app.delete("/api/history", response_model=HistoryDeleteResponse)
def clear_history() -> HistoryDeleteResponse:
    return HistoryDeleteResponse(
        deleted_count=history.delete_rewrites(),
        status="success",
    )
