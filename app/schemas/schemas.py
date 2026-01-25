from datetime import datetime
from pydantic import BaseModel


class ValidationResult(BaseModel):
    """입력 검증 결과"""

    is_valid: bool
    reject_reason: str | None = None
    messages: list[str] = []


class TaskCreate(BaseModel):
    """만화 생성 요청"""

    meeting_text: str


class TaskStatus(BaseModel):
    """작업 상태 응답"""

    id: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PanelScenario(BaseModel):
    """4컷 만화 각 패널의 시나리오"""

    episode_number: int
    image_prompt: str


class ComicResponse(BaseModel):
    """생성된 만화 응답"""

    id: str
    task_id: str
    part_number: int
    panels: list[PanelScenario]
    image_paths: list[str]
    created_at: datetime


class GenerateResponse(BaseModel):
    """만화 생성 요청 응답 (검증 통과 시)"""

    task: TaskStatus
    messages: list[str] = []


class TaskResponse(BaseModel):
    """작업 결과 응답"""

    task: TaskStatus
    comics: list[ComicResponse] = []
