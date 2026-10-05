from typing import Any
from pydantic import BaseModel, Field


class ClusteredRequirementItem(BaseModel):
    id: int
    req_key: str
    text: str
    classification_label: str | None = None
    section: str | None = None


class ClusterGroup(BaseModel):
    cluster_id: int
    label: str = Field(..., description="Auto-generated descriptive topic label derived from top TF-IDF keywords")
    keywords: list[str] = Field(default_factory=list, description="Top distinguishing TF-IDF keywords")
    size: int = Field(..., description="Number of requirements in this cluster")
    requirements: list[ClusteredRequirementItem]


class DocumentClustersResponse(BaseModel):
    document_id: int
    total_requirements: int
    num_clusters: int
    clusters: list[ClusterGroup]
