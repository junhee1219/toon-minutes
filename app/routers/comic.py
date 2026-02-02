import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, File, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Task, Comic, Visitor
from app.schemas import TaskCreate, TaskStatus, TaskResponse, ComicResponse, PanelScenario, GenerateResponse, TaskHistoryItem, HistoryResponse
from app.services.comic_service import comic_service
from app.services.llm_service import llm_service
from app.utils import generate_nickname

router = APIRouter(tags=["comic"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_comic(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """만화 생성 요청 (입력 검증 포함)"""
    # 1. Visitor 조회
    visitor_id = None
    nickname = None
    if request.visitor_id:
        visitor = await db.get(Visitor, request.visitor_id)
        if visitor:
            visitor_id = visitor.id
            nickname = visitor.nickname

    # 2. 입력 검증 + 대기 메시지 생성
    validation = await llm_service.validate_input(request.meeting_text)

    # 3. Task 생성 (거부/통과 모두 저장)
    task = Task(
        visitor_id=visitor_id,
        meeting_text=request.meeting_text,
        is_valid=validation.is_valid,
        reject_reason=validation.reject_reason,
        status="rejected" if not validation.is_valid else "pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=validation.reject_reason or "만화로 변환할 수 없는 입력입니다.",
        )

    # 3. 백그라운드에서 만화 생성
    background_tasks.add_task(
        comic_service.create_comic,
        db,
        task.id,
        request.meeting_text,
    )

    return GenerateResponse(
        task=TaskStatus(
            id=task.id,
            status=task.status,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        messages=validation.messages,
        nickname=nickname,
    )


@router.post("/generate-with-images", response_model=GenerateResponse)
async def generate_comic_with_images(
    background_tasks: BackgroundTasks,
    meeting_text: str = Form(...),
    visitor_id: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
):
    """만화 생성 요청 (이미지 포함)"""
    # 1. Visitor 조회
    db_visitor_id = None
    nickname = None
    if visitor_id:
        visitor = await db.get(Visitor, visitor_id)
        if visitor:
            db_visitor_id = visitor.id
            nickname = visitor.nickname

    # 2. 이미지 파일 읽기
    image_bytes_list = []
    for img in images:
        if img.filename:
            content = await img.read()
            if content:
                image_bytes_list.append(content)

    # 3. 입력 검증 + 대기 메시지 생성
    validation = await llm_service.validate_input(meeting_text)

    # 4. Task 생성
    task = Task(
        visitor_id=db_visitor_id,
        meeting_text=meeting_text,
        is_valid=validation.is_valid,
        reject_reason=validation.reject_reason,
        status="rejected" if not validation.is_valid else "pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    if not validation.is_valid:
        raise HTTPException(
            status_code=400,
            detail=validation.reject_reason or "만화로 변환할 수 없는 입력입니다.",
        )

    # 5. 백그라운드에서 만화 생성 (이미지 포함)
    background_tasks.add_task(
        comic_service.create_comic,
        db,
        task.id,
        meeting_text,
        image_bytes_list,
    )

    return GenerateResponse(
        task=TaskStatus(
            id=task.id,
            status=task.status,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        messages=validation.messages,
        nickname=nickname,
    )


def get_client_ip(request: Request) -> str:
    """요청에서 클라이언트 IP 추출 (ngrok X-Forwarded-For 지원)"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/visitor")
async def get_or_create_visitor(
    request: Request,
    id: str = "",
    db: AsyncSession = Depends(get_db),
):
    """방문자 조회/생성, 닉네임 반환"""
    client_ip = get_client_ip(request)
    visitor = None

    if id:
        visitor = await db.get(Visitor, id)
        if visitor:
            visitor.visit_count += 1
            visitor.last_ip = client_ip
            await db.commit()

    if not visitor:
        visitor = Visitor(
            nickname=generate_nickname(),
            ip_address=client_ip,
            last_ip=client_ip,
            visit_count=1,
        )
        db.add(visitor)
        await db.commit()
        await db.refresh(visitor)

    return {"id": visitor.id, "nickname": visitor.nickname}


@router.get("/history/{visitor_id}", response_model=HistoryResponse)
async def get_history(visitor_id: str, db: AsyncSession = Depends(get_db)):
    """방문자의 작업 내역 조회 (최근 20개)"""
    # visitor 확인
    visitor = await db.get(Visitor, visitor_id)
    if not visitor:
        return HistoryResponse(tasks=[])

    # 최근 작업 조회 (completed, processing, pending만)
    result = await db.execute(
        select(Task)
        .where(Task.visitor_id == visitor_id)
        .where(Task.status.in_(["completed", "processing", "pending"]))
        .order_by(Task.created_at.desc())
        .limit(20)
    )
    tasks = result.scalars().all()

    history_items = []
    for task in tasks:
        # 첫 번째 이미지 URL 가져오기
        thumbnail_url = None
        if task.status == "completed":
            comic_result = await db.execute(
                select(Comic).where(Comic.task_id == task.id).limit(1)
            )
            comic = comic_result.scalar_one_or_none()
            if comic and comic.image_paths:
                image_paths = json.loads(comic.image_paths)
                if image_paths:
                    thumbnail_url = image_paths[0]

        history_items.append(
            TaskHistoryItem(
                id=task.id,
                status=task.status,
                meeting_text_preview=task.meeting_text[:50] + ("..." if len(task.meeting_text) > 50 else ""),
                thumbnail_url=thumbnail_url,
                created_at=task.created_at,
            )
        )

    return HistoryResponse(tasks=history_items)


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str, db: AsyncSession = Depends(get_db)):
    """작업 상태 조회"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(
        id=task.id,
        status=task.status,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/result/{task_id}", response_model=TaskResponse)
async def get_result(task_id: str, db: AsyncSession = Depends(get_db)):
    """생성 결과 조회"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(select(Comic).where(Comic.task_id == task_id))
    comics = result.scalars().all()

    comic_responses = []
    for comic in comics:
        panels_data = json.loads(comic.panels_json) if comic.panels_json else []
        panels = [PanelScenario(**p) for p in panels_data]
        image_paths = json.loads(comic.image_paths) if comic.image_paths else []

        comic_responses.append(
            ComicResponse(
                id=comic.id,
                task_id=comic.task_id,
                part_number=comic.part_number,
                panels=panels,
                image_paths=image_paths,
                created_at=comic.created_at,
            )
        )

    return TaskResponse(
        task=TaskStatus(
            id=task.id,
            status=task.status,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        comics=comic_responses,
    )
