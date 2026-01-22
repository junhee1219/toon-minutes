import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db
from app.models import Task, Comic
from app.routers import comic


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 이벤트"""
    await init_db()
    yield


app = FastAPI(
    title="Toon-Minutes",
    description="회의록을 4컷 만화로 변환하는 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
templates = Jinja2Templates(directory="app/templates")

# 라우터 등록
app.include_router(comic.router)


@app.get("/")
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/view/{task_id}")
async def view_result(request: Request, task_id: str, db: AsyncSession = Depends(get_db)):
    """결과 페이지 (HTML)"""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await db.execute(select(Comic).where(Comic.task_id == task_id))
    comics = result.scalars().all()

    # 템플릿용 데이터 변환
    comics_data = []
    for comic in comics:
        panels = json.loads(comic.panels_json) if comic.panels_json else []
        image_paths = json.loads(comic.image_paths) if comic.image_paths else []
        comics_data.append({
            "part_number": comic.part_number,
            "panels": panels,
            "image_paths": image_paths,
        })

    return templates.TemplateResponse("result.html", {
        "request": request,
        "task": task,
        "comics": comics_data,
    })
