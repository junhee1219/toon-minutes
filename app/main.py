from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
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
