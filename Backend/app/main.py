from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.database import get_db, engine, Base
from app.routers import auth, applications, followups

# Create missing tables on startup (models must be imported above)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Application Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers = connect each API group to the app
app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(followups.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Job Tracker API is running"}


@app.get("/health/db", tags=["Health"])
def db_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "connected"}