from typing import get_args

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import require_admin
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import APIRouter, Depends, HTTPException, Query, Response


# dependencies=[...] = EVERY route in this router is admin-only (403 for normal user)
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


# ---------- Admin API 1: GET /admin/stats ----------
# Totals across ALL users: users, active users, applications, count per stage
@router.get("/stats", response_model=schemas.AdminStatsOut)
def admin_stats(db: Session = Depends(get_db)):
    total_users = db.query(func.count(models.User.id)).scalar()
    active_users = (
        db.query(func.count(models.User.id))
        .filter(models.User.is_active.is_(True))
        .scalar()
    )
    total_applications = db.query(func.count(models.Application.id)).scalar()

    # One GROUP BY query gives count per stage
    rows = (
        db.query(models.Application.status, func.count(models.Application.id))
        .group_by(models.Application.status)
        .all()
    )

    # Start every stage at 0, so empty stages still show in response
    per_stage = {stage: 0 for stage in get_args(schemas.Status)}
    for status, count in rows:
        per_stage[status] = count

    return schemas.AdminStatsOut(
        total_users=total_users,
        active_users=active_users,
        total_applications=total_applications,
        applications_per_stage=per_stage,
    )

# ---------- Admin API 2: GET /admin/users ----------
# List all users + how many applications each have. Search, filter, pagination
@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    search: str | None = Query(default=None, description="Search name or email"),
    is_active: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    # LEFT JOIN so users with 0 applications still show. COUNT per user via GROUP BY
    query = (
        db.query(models.User, func.count(models.Application.id))
        .outerjoin(models.Application, models.Application.user_id == models.User.id)
        .group_by(models.User.id)
    )

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(models.User.name.ilike(like), models.User.email.ilike(like))
        )
    if is_active is not None:
        query = query.filter(models.User.is_active.is_(is_active))

    rows = query.order_by(models.User.id).offset(offset).limit(limit).all()

    return [
        schemas.AdminUserOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            applications_count=count,
        )
        for user, count in rows
    ]

# ---------- Admin API 3: PATCH /admin/users/{user_id}/status ----------
# Activate / deactivate a user. Admin cannot change own status (lockout guard)
@router.patch("/users/{user_id}/status", response_model=schemas.AdminUserOut)
def set_user_status(
    user_id: int,
    data: schemas.AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own status")

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = data.is_active
    db.commit()
    db.refresh(user)

    applications_count = (
        db.query(func.count(models.Application.id))
        .filter(models.Application.user_id == user.id)
        .scalar()
    )

    return schemas.AdminUserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        applications_count=applications_count,
    )

# ---------- Admin API 4: DELETE /admin/users/{user_id} ----------
# Permanently delete a user + all their applications and follow-ups (cascade)
@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Other admin must be demoted first. Stops accidental admin wipe.
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete an admin account")

    db.delete(user)  # ORM cascade removes applications → follow-ups
    db.commit()
    return Response(status_code=204)

# ---------- Admin API 5: GET /admin/users/{user_id}/applications ----------
# Admin view of one user's applications. Summary fields only (privacy)
@router.get(
    "/users/{user_id}/applications",
    response_model=list[schemas.AdminApplicationOut],
)
def list_user_applications(
    user_id: int,
    status: schemas.Status | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if db.get(models.User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(models.Application).filter(models.Application.user_id == user_id)
    if status:
        query = query.filter(models.Application.status == status)

    return (
        query.order_by(models.Application.created_at.desc(), models.Application.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )