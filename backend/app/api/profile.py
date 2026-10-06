"""
SRS Guardian — User Profile API Router (Phase 18.2)

Provides endpoints to retrieve and maintain the authoritative reviewer / engineer personal details.
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db, engine, Base
from backend.app.models.user_profile import UserProfile
from backend.app.schemas.user_profile import UserProfileUpdate, UserProfileResponse

logger = logging.getLogger(__name__)

# Ensure user_profiles table is created
Base.metadata.create_all(bind=engine)

router = APIRouter()


@router.get(
    "",
    response_model=UserProfileResponse,
    summary="Get the authoritative user profile and reviewer details",
)
def get_user_profile(db: Session = Depends(get_db)):
    profile = db.query(UserProfile).order_by(UserProfile.id.asc()).first()
    if not profile:
        profile = UserProfile(
            full_name=None,
            email=None,
            organization=None,
            role=None,
            phone=None,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put(
    "",
    response_model=UserProfileResponse,
    summary="Update and persist the authoritative user profile and reviewer details",
)
def update_user_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
):
    profile = db.query(UserProfile).order_by(UserProfile.id.asc()).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)

    if profile_data.full_name is not None:
        profile.full_name = profile_data.full_name.strip() or None
    if profile_data.email is not None:
        profile.email = profile_data.email.strip() or None
    if profile_data.organization is not None:
        profile.organization = profile_data.organization.strip() or None
    if profile_data.role is not None:
        profile.role = profile_data.role.strip() or None
    if profile_data.phone is not None:
        profile.phone = profile_data.phone.strip() or None

    db.commit()
    db.refresh(profile)
    logger.info(f"Updated user profile for: {profile.full_name or 'Anonymous'}")
    return profile
