"""Pydantic data contracts: Document, Entity, Relationship, ChatResponse."""

from typing import Literal

from pydantic import BaseModel, Field

DocType = Literal["adverse_event", "rca", "protocol", "formulary"]
EntityType = Literal[
    "medication", "department", "incident_type", "staff_role", "root_cause", "protocol"
]


class Document(BaseModel):
    doc_id: str
    doc_type: DocType
    title: str
    content: str
    metadata: dict = Field(default_factory=dict)
    gcs_uri: str = ""


class Entity(BaseModel):
    name: str
    type: EntityType
    doc_ids: list[str] = Field(default_factory=list)


class Relationship(BaseModel):
    source: str
    target: str
    relation: str
    doc_ids: list[str] = Field(default_factory=list)
    weight: int = 1


class Citation(BaseModel):
    doc_id: str
    title: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    entities_used: list[str] = Field(default_factory=list)
