from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

STAGES = ["Applied", "Screening", "Interview", "Offer", "Accepted"]


# ---------- GET /dashboard/stats ----------
# Count of applications per status (only current user's)
@router.get("/stats", response_model=schemas.DashboardStatsOut)
def dashboard_stats(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.Application.status, func.count(models.Application.id))
        .filter(models.Application.user_id == user.id)
        .group_by(models.Application.status)
        .all()
    )
    by_status = {stage: 0 for stage in STAGES}  # zero-fill so chart never misses a stage
    for status, count in rows:
        by_status[status] = count  # extra statuses like "Rejected" also appear
    return schemas.DashboardStatsOut(total=sum(by_status.values()), by_status=by_status)


# ---------- GET /dashboard/response-rate ----------
# % of applications that moved past "Applied"
@router.get("/response-rate", response_model=schemas.ResponseRateOut)
def response_rate(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    base = db.query(func.count(models.Application.id)).filter(
        models.Application.user_id == user.id
    )
    total = base.scalar() or 0
    responded = base.filter(models.Application.status != "Applied").scalar() or 0
    rate = round(responded * 100 / total, 1) if total else 0.0
    return schemas.ResponseRateOut(total=total, responded=responded, response_rate=rate)


# ---------- GET /dashboard/timeline ----------
# Applications per month, based on applied_date (MySQL DATE_FORMAT)
@router.get("/timeline", response_model=list[schemas.TimelinePointOut])
def timeline(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    month = func.date_format(models.Application.applied_date, "%Y-%m")
    rows = (
        db.query(month.label("month"), func.count(models.Application.id))
        .filter(
            models.Application.user_id == user.id,
            models.Application.applied_date.isnot(None),
        )
        .group_by(month)
        .order_by(month)
        .all()
    )
    return [schemas.TimelinePointOut(month=m, count=c) for m, c in rows]

# ---------- Dashboard ----------
class DashboardStatsOut(BaseModel):
    total: int
    by_status: dict[str, int]


class ResponseRateOut(BaseModel):
    total: int
    responded: int
    response_rate: float  # percent, e.g. 28.0


class TimelinePointOut(BaseModel):
    month: str  # "2026-10"
    count: int