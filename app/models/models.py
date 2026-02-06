from uuid_extensions import uuid7str
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Float
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return uuid7str()


class Visitor(Base):
    """방문자"""

    __tablename__ = "visitors"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    nickname = Column(String(30), nullable=True)
    ip_address = Column(String(45), nullable=True)  # 최초 접속 IP (IPv6 대응)
    last_ip = Column(String(45), nullable=True)     # 마지막 접속 IP
    first_seen = Column(DateTime, default=now_kst)
    last_seen = Column(DateTime, default=now_kst, onupdate=now_kst)
    visit_count = Column(Integer, default=0)

    tasks = relationship("Task", back_populates="visitor")


class Task(Base):
    """만화 생성 작업"""

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    visitor_id = Column(String(36), ForeignKey("visitors.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending | processing | completed | failed | rejected
    meeting_text = Column(Text, nullable=False)
    is_valid = Column(Boolean, default=True)
    reject_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    character_sheet_url = Column(Text, nullable=True)  # 캐릭터 시트 이미지 URL (내부용)
    meeting_img = Column(Text, nullable=True)  # 첨부 이미지 S3 URL (JSON array)
    # 소요시간 (초)
    scenario_duration = Column(Float, nullable=True)  # 시나리오 생성
    character_sheet_duration = Column(Float, nullable=True)  # 캐릭터 시트 생성
    episode_image_duration = Column(Float, nullable=True)  # 에피소드 이미지 생성
    total_duration = Column(Float, nullable=True)  # 총 소요시간
    created_at = Column(DateTime, default=now_kst)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)

    visitor = relationship("Visitor", back_populates="tasks")
    comics = relationship("Comic", back_populates="task", cascade="all, delete-orphan")
    api_logs = relationship("ApiLog", back_populates="task", cascade="all, delete-orphan")


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


class ApiLog(Base):
    """외부 API 호출 로그"""

    __tablename__ = "api_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
    service = Column(String(20))        # "llm" | "image"
    method = Column(String(50))         # "analyze_meeting", "validate_input", "generate_image", etc.
    model = Column(String(50))          # "gemini-3-flash-preview", "gemini-3-pro-image-preview"
    request_body = Column(Text)         # 프롬프트/config JSON
    response_body = Column(Text)        # 응답 메타데이터 JSON
    status = Column(String(10))         # "success" | "error"
    error_message = Column(Text, nullable=True)
    duration = Column(Float)            # 초 단위
    attempt = Column(Integer, default=1)  # 재시도 횟수 (1~3)
    created_at = Column(DateTime, default=now_kst)

    task = relationship("Task", back_populates="api_logs")
