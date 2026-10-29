from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/applications", tags=["Applications"])


def get_owned_application(
    app_id: int, db: Session, user: models.User
) -> models.Application:
    """Fetch one application. Must belong to current user, else 404."""
    application = (
        db.query(models.Application)
        .filter(models.Application.id == app_id, models.Application.user_id == user.id)
        .first()
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("", response_model=schemas.ApplicationOut, status_code=201)
def create_application(
    data: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    values = data.model_dump()
    if values["applied_date"] is None:
        values["applied_date"] = date.today()

    application = models.Application(**values, user_id=user.id)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[schemas.ApplicationOut])
def list_applications(
    status: schemas.Status | None = None,
    search: str | None = Query(default=None, description="Search company name"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(models.Application).filter(models.Application.user_id == user.id)

    if status:
        query = query.filter(models.Application.status == status)
    if search:
        query = query.filter(models.Application.company.ilike(f"%{search}%"))

    return (
        query.order_by(models.Application.created_at.desc(), models.Application.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{app_id}", response_model=schemas.ApplicationOut)
def get_application(
    app_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return get_owned_application(app_id, db, user)


@router.put("/{app_id}", response_model=schemas.ApplicationOut)
def update_application(
    app_id: int,
    data: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    application = get_owned_application(app_id, db, user)

    # exclude_unset = only fields client really sent
    changes = data.model_dump(exclude_unset=True)

    # Required columns can't be set to null
    for field in ("company", "role_title", "status"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")

    for field, value in changes.items():
        setattr(application, field, value)

    db.commit()
    db.refresh(application)
    return application


@router.patch("/{app_id}/status", response_model=schemas.ApplicationOut)
def update_status(
    app_id: int,
    data: schemas.ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    application = get_owned_application(app_id, db, user)
    application.status = data.status
    db.commit()
    db.refresh(application)
    return application


@router.delete("/{app_id}", status_code=204)
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    application = get_owned_application(app_id, db, user)
    db.delete(application)
    db.commit()
    return Response(status_code=204)