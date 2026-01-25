import uuid
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Task(Base):
    """만화 생성 작업"""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    status = Column(String(20), default="pending")  # pending | processing | completed | failed
    meeting_text = Column(Text, nullable=False)
    is_valid = Column(Boolean, default=True)
    reject_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now_kst)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)

    comics = relationship("Comic", back_populates="task", cascade="all, delete-orphan")


class Comic(Base):
    """생성된 만화"""

    __tablename__ = "comics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    part_number = Column(Integer, default=1)
    panels_json = Column(Text, nullable=True)  # 4컷 시나리오 JSON
    image_paths = Column(Text, nullable=True)  # 이미지 경로 JSON array
    created_at = Column(DateTime, default=now_kst)

    task = relationship("Task", back_populates="comics")


