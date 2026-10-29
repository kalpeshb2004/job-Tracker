from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.applications import get_owned_application
from app.security import get_current_user

router = APIRouter(tags=["Follow-ups"])


# ---------- Helper (not an API) ----------
def get_owned_followup(
    followup_id: int, db: Session, user: models.User
) -> models.FollowUp:
    """Follow-up has no user_id. Ownership go through its application."""
    followup = (
        db.query(models.FollowUp)
        .join(models.Application, models.FollowUp.application_id == models.Application.id)
        .filter(models.FollowUp.id == followup_id, models.Application.user_id == user.id)
        .first()
    )
    if followup is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return followup


# ---------- API 1: POST /applications/{app_id}/followups ----------
# Add new follow-up to one application
@router.post(
    "/applications/{app_id}/followups",
    response_model=schemas.FollowUpOut,
    status_code=201,
)
def create_followup(
    app_id: int,
    data: schemas.FollowUpCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    application = get_owned_application(app_id, db, user)  # 404 if not yours
    followup = models.FollowUp(application_id=application.id, **data.model_dump())
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


# ---------- API 2: GET /applications/{app_id}/followups ----------
# List all follow-ups of one application, sorted by date
@router.get(
    "/applications/{app_id}/followups",
    response_model=list[schemas.FollowUpOut],
)
def list_followups(
    app_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    application = get_owned_application(app_id, db, user)
    return (
        db.query(models.FollowUp)
        .filter(models.FollowUp.application_id == application.id)
        .order_by(models.FollowUp.followup_date)
        .all()
    )


# ---------- API 3: GET /followups/upcoming ----------
# Dashboard list: not-done follow-ups due in next N days (overdue included)
@router.get("/followups/upcoming", response_model=list[schemas.UpcomingFollowUpOut])
def upcoming_followups(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    end = date.today() + timedelta(days=days)
    rows = (
        db.query(models.FollowUp, models.Application.company, models.Application.role_title)
        .join(models.Application, models.FollowUp.application_id == models.Application.id)
        .filter(
            models.Application.user_id == user.id,
            models.FollowUp.is_done.is_(False),
            models.FollowUp.followup_date <= end,
        )
        .order_by(models.FollowUp.followup_date)
        .all()
    )
    return [
        schemas.UpcomingFollowUpOut(
            id=f.id,
            application_id=f.application_id,
            followup_date=f.followup_date,
            note=f.note,
            is_done=f.is_done,
            reminder_sent=f.reminder_sent,
            company=company,
            role_title=role_title,
        )
        for f, company, role_title in rows
    ]


# ---------- API 4: PUT /followups/{followup_id} ----------
# Edit follow-up: change date / note, or mark done
@router.put("/followups/{followup_id}", response_model=schemas.FollowUpOut)
def update_followup(
    followup_id: int,
    data: schemas.FollowUpUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    followup = get_owned_followup(followup_id, db, user)
    changes = data.model_dump(exclude_unset=True)

    for field in ("followup_date", "is_done"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")

    # Date moved → reminder email must fire again for new date
    if "followup_date" in changes and changes["followup_date"] != followup.followup_date:
        followup.reminder_sent = False

    for field, value in changes.items():
        setattr(followup, field, value)

    db.commit()
    db.refresh(followup)
    return followup


# ---------- API 5: DELETE /followups/{followup_id} ----------
# Delete one follow-up
@router.delete("/followups/{followup_id}", status_code=204)
def delete_followup(
    followup_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    followup = get_owned_followup(followup_id, db, user)
    db.delete(followup)
    db.commit()
    return Response(status_code=204)