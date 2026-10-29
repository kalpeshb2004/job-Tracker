from pydantic import BaseModel, EmailStr, Field, ConfigDict

from datetime import date, datetime
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