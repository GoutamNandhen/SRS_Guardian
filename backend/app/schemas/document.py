from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    page_count: int
    status: str


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    page_count: int
    status: str
    uploaded_at: datetime
    requirement_count: int = 0


class DocumentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    file_size: int
    page_count: int
    status: str
    uploaded_at: datetime
    raw_text: str
    cleaned_text: str
    version: str | None = None
    requirement_count: int = 0
