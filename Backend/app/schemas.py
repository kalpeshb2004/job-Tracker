from pydantic import BaseModel, EmailStr, Field, ConfigDict

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from typing import Literal

# Allowed stages. Wrong value → FastAPI auto return 422.
Status = Literal["Applied", "Screening", "Interview", "Offer", "Accepted", "Rejected"]

# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=50)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Applications ----------
class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=150)
    role_title: str = Field(min_length=1, max_length=150)
    status: Status = "Applied"
    applied_date: date | None = None
    deadline: date | None = None
    source: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    job_description: str | None = None


class ApplicationUpdate(BaseModel):
    # All optional. Client send only fields it want to change.
    company: str | None = Field(default=None, min_length=1, max_length=150)
    role_title: str | None = Field(default=None, min_length=1, max_length=150)
    status: Status | None = None
    applied_date: date | None = None
    deadline: date | None = None
    source: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    job_description: str | None = None


class ApplicationStatusUpdate(BaseModel):
    status: Status


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company: str
    role_title: str
    status: str
    applied_date: date | None
    deadline: date | None
    source: str | None
    notes: str | None
    job_description: str | None
    match_score: float | None
    created_at: datetime | None

class FollowUpCreate(BaseModel):
    followup_date: date
    note: str | None = None


class FollowUpUpdate(BaseModel):
    followup_date: date | None = None
    note: str | None = None
    is_done: bool | None = None


class FollowUpOut(BaseModel):
    id: int
    application_id: int
    followup_date: date
    note: str | None = None
    is_done: bool
    reminder_sent: bool

    model_config = ConfigDict(from_attributes=True)


class UpcomingFollowUpOut(FollowUpOut):
    company: str
    role_title: str


class DashboardStatsOut(BaseModel):
    total: int
    by_status: dict[str, int]


class ResponseRateOut(BaseModel):
    total: int
    responded: int
    response_rate: float  # percentage, 0 to 100


class TimelinePointOut(BaseModel):
    month: str  # "2026-10"
    count: int

# ---------- Admin ----------
class AdminStatsOut(BaseModel):
    total_users: int
    active_users: int
    total_applications: int
    applications_per_stage: dict[str, int]

class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime | None
    applications_count: int

class AdminUserStatusUpdate(BaseModel):
    is_active: bool

class AdminApplicationOut(BaseModel):
    # Summary only. No notes / job_description (user's private data)
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company: str
    role_title: str
    status: str
    applied_date: date | None
    source: str | None
    created_at: datetime | None