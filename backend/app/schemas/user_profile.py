"""
SRS Guardian — Schemas for User Profile (Phase 18.2)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: Optional[datetime] = None
