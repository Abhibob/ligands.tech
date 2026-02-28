"""Pydantic models for bind-qmd, matching schemas/qmd-query.schema.json and qmd-result.schema.json."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


class QmdQuerySpec(BaseModel):
    text: str
    collections: list[str] = Field(default_factory=list)
    strategy: Literal["keyword", "semantic", "hybrid"] = "keyword"
    top_k: int = Field(5, alias="topK")
    kind: Literal["skill", "spec", "schema", "example", "note", "any"] = "any"
    paths_only: bool = Field(False, alias="pathsOnly")
    full: bool = False
    line_numbers: bool = Field(False, alias="lineNumbers")
    rerank: bool = False
    tags: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list, alias="mustInclude")
    must_exclude: list[str] = Field(default_factory=list, alias="mustExclude")

    model_config = {"populate_by_name": True}


class QmdQueryRequest(BaseRequest):
    kind: str = "QmdQueryRequest"
    spec: QmdQuerySpec

    model_config = {"populate_by_name": True}


class QmdSearchHit(BaseModel):
    path: str
    title: str = ""
    kind: str = "any"
    score: float = 0.0
    snippet: str = ""
    line_start: int | None = Field(None, alias="lineStart")
    line_end: int | None = Field(None, alias="lineEnd")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QmdQuerySummary(BaseModel):
    query_text: str = Field("", alias="queryText")
    strategy_used: str = Field("keyword", alias="strategyUsed")
    results: list[QmdSearchHit] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QmdQueryResult(BaseResult):
    kind: str = "QmdQueryResult"
    tool: str = "qmd"
    summary: dict[str, Any] = Field(default_factory=dict)
