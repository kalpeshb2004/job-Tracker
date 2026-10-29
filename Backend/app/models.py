from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    Boolean, Float, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")  # user / admin
    is_active = Column(Boolean, nullable=False, default=True)
    resume_path = Column(String(255), nullable=True)
    reminders_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    applications = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company = Column(String(150), nullable=False)
    role_title = Column(String(150), nullable=False)
    status = Column(String(30), nullable=False, default="Applied")
    applied_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    source = Column(String(50), nullable=True)  # LinkedIn, Naukri, Referral...
    notes = Column(Text, nullable=True)
    job_description = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="applications")
    followups = relationship(
        "FollowUp", back_populates="application", cascade="all, delete-orphan"
    )


class FollowUp(Base):
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    followup_date = Column(Date, nullable=False)
    note = Column(String(255), nullable=True)
    is_done = Column(Boolean, nullable=False, default=False)
    reminder_sent = Column(Boolean, nullable=False, default=False)

    application = relationship("Application", back_populates="followups")