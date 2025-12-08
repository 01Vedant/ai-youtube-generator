"""
Database models for DevotionalAI Platform
Uses SQLAlchemy with SQLite (local) or PostgreSQL (cloud)
"""

from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from app.config import settings
import json

# Database setup
DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================================================================
# MODELS
# =============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    
    @staticmethod
    def create(email: str, password: str, name: str):
        db = SessionLocal()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("User already exists")
        
        import uuid
        user = User(id=str(uuid.uuid4()), email=email, password_hash=password, name=name)
        db.add(user)
        db.commit()
        return user
    
    @staticmethod
    def get(user_id: str):
        db = SessionLocal()
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_by_email(email: str):
        db = SessionLocal()
        return db.query(User).filter(User.email == email).first()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    name = Column(String)
    description = Column(Text)
    story_data = Column(JSON)  # Full story structure
    settings = Column(JSON)    # Rendering settings (resolution, fps, voice, etc.)
    status = Column(String, default="draft")  # draft, in_progress, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def create(user_id: str, project_id: str, name: str, description: str, story_data: dict):
        db = SessionLocal()
        project = Project(
            id=project_id,
            user_id=user_id,
            name=name,
            description=description,
            story_data=story_data,
            settings={"resolution": "4k", "fps": 24, "voice": "aria"}
        )
        db.add(project)
        db.commit()
        return project
    
    @staticmethod
    def get(user_id: str, project_id: str):
        db = SessionLocal()
        return db.query(Project).filter(
            Project.user_id == user_id,
            Project.id == project_id
        ).first()
    
    @staticmethod
    def list_by_user(user_id: str, limit: int = 10, offset: int = 0):
        db = SessionLocal()
        return db.query(Project).filter(Project.user_id == user_id).limit(limit).offset(offset).all()
    
    @staticmethod
    def count_by_user(user_id: str):
        db = SessionLocal()
        return db.query(Project).filter(Project.user_id == user_id).count()
    
    def update(self, name=None, description=None, story_data=None, settings=None):
        db = SessionLocal()
        if name:
            self.name = name
        if description:
            self.description = description
        if story_data:
            self.story_data = story_data
        if settings:
            self.settings = {**self.settings, **settings}
        self.updated_at = datetime.utcnow()
        db.commit()
    
    def delete(self):
        db = SessionLocal()
        db.delete(self)
        db.commit()
    
    def to_dict(self):
        return {
            "project_id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "scenes": len(self.story_data.get("scenes", [])),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "story": self.story_data,
            "settings": self.settings
        }
    
    @property
    def estimated_size_gb(self):
        """Rough estimate of project size"""
        scene_count = len(self.story_data.get("scenes", []))
        # ~200MB per scene (image + audio + video)
        return (scene_count * 200 + 500) / 1024  # Add 500MB for final video overhead

class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    scene_number = Column(Integer)
    title = Column(String)
    prompt = Column(Text)
    voiceover = Column(Text)
    image_path = Column(String)
    audio_path = Column(String)
    subtitle_path = Column(String)
    status = Column(String, default="pending")  # pending, generating, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

class JobStatus(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True)
    project_id = Column(String, index=True)
    task_type = Column(String)  # tts, image_generation, subtitles, video_stitch
    status = Column(String, default="queued")  # queued, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text)
    result = Column(JSON)  # Task-specific result data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def create(job_id: str, user_id: str, project_id: str, task_type: str):
        db = SessionLocal()
        job = JobStatus(
            id=job_id,
            user_id=user_id,
            project_id=project_id,
            task_type=task_type
        )
        db.add(job)
        db.commit()
        return job
    
    @staticmethod
    def get(job_id: str):
        db = SessionLocal()
        return db.query(JobStatus).filter(JobStatus.id == job_id).first()
    
    @staticmethod
    def list_by_project(project_id: str):
        db = SessionLocal()
        return db.query(JobStatus).filter(JobStatus.project_id == project_id).order_by(JobStatus.created_at.desc()).all()
    
    def update_status(self, status: str, progress: int = None, message: str = None, result: dict = None):
        db = SessionLocal()
        self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        if result:
            self.result = result
        self.updated_at = datetime.utcnow()
        db.commit()

# Create tables
Base.metadata.create_all(bind=engine)
