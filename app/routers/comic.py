import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Task, Comic
from app.schemas import TaskCreate, TaskStatus, TaskResponse, ComicResponse, PanelScenario
from app.services.comic_service import comic_service

router = APIRouter(tags=["comic"])


@router.post("/generate", response_model=TaskStatus)
async def generate_comic(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """만화 생성 요청"""
    task = Task(meeting_text=request.meeting_text)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 백그라운드에서 만화 생성
    background_tasks.add_task(
        comic_service.create_comic,
        db,
        task.id,
        request.meeting_text,
    )

    return TaskStatus(
        id=task.id,
        status=task.status,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


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
