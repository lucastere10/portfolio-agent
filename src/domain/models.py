"""Pydantic models for the knowledge base and API contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class Metric(BaseModel):
    label: str
    value: str


class Decision(BaseModel):
    title: str
    reasoning: str


class KBEntry(BaseModel):
    id: str
    type: Literal["project", "lab", "personal_project"]
    title: str
    domain: str
    summary: str
    slug: str
    technologies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    featured: bool = False
    related_projects: list[str] = Field(default_factory=list)
    tagline: str = ""
    context: str = ""
    challenges: list[str] = Field(default_factory=list)
    learnings: list[str] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    demonstrates: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    tradeoffs: str = ""
    implementation: str = ""
    narrative: list[str] = Field(default_factory=list)
    interaction_prompt: str = ""
    demo_url: str = ""
    github_url: str = ""
    repo_url: str = ""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = None
    context: dict = Field(default_factory=dict)


class ProjectMatch(BaseModel):
    id: str
    type: Literal["project", "lab", "personal_project"]
    title: str
    score: float
    slug: str


class ChatResponse(BaseModel):
    message: str
    selected_project: str | None
    selected_type: Literal["project", "lab", "personal_project"] | None
    matches: list[ProjectMatch]
    session_id: str
    tool_used: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=20)
    filter_type: Literal["project", "lab", "personal_project", "all"] = "all"


class SearchResponse(BaseModel):
    query: str
    results: list[ProjectMatch]
    total: int


class ProjectDetail(BaseModel):
    id: str
    type: Literal["project", "lab", "personal_project"]
    title: str
    domain: str
    summary: str
    slug: str
    technologies: list[str]
    tags: list[str]
    categories: list[str]
    difficulty: str
    featured: bool
    related_projects: list[str]
    tagline: str
    context: str
    challenges: list[str]
    learnings: list[str]
    metrics: list[Metric]
    demonstrates: list[str]
    decisions: list[Decision] = Field(default_factory=list)
    tradeoffs: str = ""
    implementation: str = ""
    narrative: list[str] = Field(default_factory=list)
    interaction_prompt: str
    demo_url: str = ""
    github_url: str = ""
    repo_url: str = ""


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
