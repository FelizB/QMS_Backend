# app/presentation/controllers/users_skills.py (top of file)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.presentation.schemas.user_skills import UserSkillIn, UserSkillOut, BulkSkillsResult, BulkSkillsIn, \
    DeleteResponse
from app.infrastructure.models.user_skills import UserSkill
from app.infrastructure.models.user_model import User  # <-- import your User model
from app.core.db import get_session

skills_router = APIRouter(prefix="/users/{user_id}/skills", tags=["users_skills"])


async def get_user_or_404(user_id: int, db: AsyncSession) -> User:
    """
    Ensure the parent user exists (and isn’t soft-deleted, if you use soft deletes).
    Returns the user instance if found; raises 404 otherwise.
    """
    user = await db.get(User, user_id)
    # If you have a soft-delete column like `active` or `deleted`, check it too:
    if not user or getattr(user, "deleted", False) or getattr(user, "active", True) is False:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def normalize_name(name: str) -> str:
    """Trim and collapse internal whitespace for a consistent uniqueness check."""
    return " ".join(name.split()).strip()


@skills_router.get("", response_model=list[UserSkillOut])
async def list_skills(user_id: int, db: AsyncSession = Depends(get_session)):
    # Ensure user exists first
    await get_user_or_404(user_id, db)

    res = await db.execute(
        select(UserSkill)
        .where(UserSkill.user_id == user_id)
        .order_by(UserSkill.name.asc())
    )
    return [UserSkillOut.model_validate(row) for row in res.scalars().all()]


@skills_router.post("", response_model=UserSkillOut, status_code=201)
async def add_skill(user_id: int, payload: UserSkillIn, db: AsyncSession = Depends(get_session)):
    await get_user_or_404(user_id, db)

    name_norm = normalize_name(payload.name)

    # Optional: proactive duplicate check (case-insensitive)
    exists = await db.scalar(
        select(func.count(UserSkill.id))
        .where(
            UserSkill.user_id == user_id,
            func.lower(UserSkill.name) == func.lower(name_norm),
        )
    )
    if exists and int(exists) > 0:
        raise HTTPException(status_code=409, detail="Skill with the same name already exists for this user")

    skill = UserSkill(user_id=user_id, name=name_norm, percent=payload.percent)
    db.add(skill)
    try:
        await db.commit()
    except IntegrityError:
        # In case the DB UNIQUE constraint catches a race condition
        await db.rollback()
        raise HTTPException(status_code=409, detail="Skill with the same name already exists for this user")

    await db.refresh(skill)
    return UserSkillOut.model_validate(skill)


@skills_router.put("/{skill_id}", response_model=UserSkillOut)
async def update_skill(user_id: int, skill_id: int, payload: UserSkillIn, db: AsyncSession = Depends(get_session)):
    await get_user_or_404(user_id, db)

    skill = await db.get(UserSkill, skill_id)
    if not skill or skill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")

    name_norm = normalize_name(payload.name)

    # Check duplicates if the name is changing (case-insensitive)
    if name_norm.lower() != skill.name.lower():
        dup = await db.scalar(
            select(func.count(UserSkill.id))
            .where(
                UserSkill.user_id == user_id,
                func.lower(UserSkill.name) == func.lower(name_norm),
                UserSkill.id != skill_id,
            )
        )
        if dup and int(dup) > 0:
            raise HTTPException(status_code=409, detail="Another skill with this name already exists for this user")

    skill.name = name_norm
    skill.percent = payload.percent
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Another skill with this name already exists for this user")

    await db.refresh(skill)
    return UserSkillOut.model_validate(skill)


@skills_router.delete("/{skill_id}", response_model=DeleteResponse)
async def delete_skill(user_id: int, skill_id: int, db: AsyncSession = Depends(get_session)):
    await get_user_or_404(user_id, db)

    skill = await db.get(UserSkill, skill_id)
    if not skill or skill.user_id != user_id:
        raise HTTPException(status_code=404, detail="Skill not found")

    await db.delete(skill)
    await db.commit()
    return DeleteResponse(message=f"{skill.name} deleted successfully")


@skills_router.post("/bulk", response_model=BulkSkillsResult)
async def bulk_add_skills(
        user_id: int,
        payload: BulkSkillsIn,
        db: AsyncSession = Depends(get_session),
):
    await get_user_or_404(user_id, db)

    # 1) Normalize + validate + dedup within payload (case-insensitive by name)
    normalized: list[UserSkillIn] = []
    seen_lower: set[str] = set()
    skipped_duplicates: list[str] = []

    for s in payload.skills:
        nm = normalize_name(s.name)
        if not nm:
            # skip empty names silently, or raise 422 if you prefer
            skipped_duplicates.append(s.name)
            continue
        key = nm.lower()
        if key in seen_lower:
            skipped_duplicates.append(nm)  # duplicate in incoming list
            continue
        seen_lower.add(key)
        normalized.append(UserSkillIn(name=nm, percent=s.percent))

    if not normalized:
        return BulkSkillsResult(created=[], skipped_duplicates=skipped_duplicates)

    # 2) Load existing names for this user (case-insensitive) to skip those
    existing_rows = await db.execute(
        select(func.lower(UserSkill.name))
        .where(UserSkill.user_id == user_id)
    )
    existing_lower = set(existing_rows.scalars().all())

    to_create: list[UserSkill] = []
    for s in normalized:
        if s.name.lower() in existing_lower:
            skipped_duplicates.append(s.name)
            continue
        to_create.append(UserSkill(user_id=user_id, name=s.name, percent=s.percent))

    if not to_create:
        return BulkSkillsResult(created=[], skipped_duplicates=skipped_duplicates)

    # 3) Insert in one transaction
    db.add_all(to_create)
    try:
        await db.commit()
    except IntegrityError:
        # In case of race (another insert happened concurrently), rollback and recompute created list
        await db.rollback()
        # Re-fetch and filter again; only create those still missing (optional: retry once)
        # For simplicity, return as skipped on conflict
        skipped_duplicates.extend(s.name for s in to_create)
        return BulkSkillsResult(created=[], skipped_duplicates=sorted(set(skipped_duplicates)))

    # refresh to get IDs
    for obj in to_create:
        await db.refresh(obj)

    created = [UserSkillOut.model_validate(obj) for obj in to_create]
    return BulkSkillsResult(
        created=created,
        skipped_duplicates=...,
    )
