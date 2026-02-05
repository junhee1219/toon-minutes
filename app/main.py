import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db
from app.models import Task, Comic
from app.routers import comic
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)


async def _health_check_loop() -> None:
    """20분마다 헬스체크 알림"""
    while True:
        await asyncio.sleep(20 * 60)
        telegram_service.notify_health_check()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 이벤트"""
    # dev 환경에서만 테이블 자동 생성 (Spring ddl-auto=update와 유사)
    if settings.env == "DEV":
        await init_db()
        logger.info("Dev mode: Database tables auto-created")
    telegram_service.notify_server_started()
    health_task = asyncio.create_task(_health_check_loop())
    yield
    health_task.cancel()


app = FastAPI(
    title="toonify",
    description="4컷 만화로 변환하는 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://*.github.io",
    ],
    allow_origin_regex=r"https://.*\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
