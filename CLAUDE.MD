# Toon-Minutes Backend

## 프로젝트 개요

회의록을 4컷 만화로 변환하는 서비스의 백엔드 애플리케이션.

### 핵심 워크플로우
1. **Input**: 사용자가 회의록 텍스트 입력
2. **LLM 분석**: Gemini가 회의록을 분석하여 4컷 시나리오 생성
3. **이미지 생성**: NanoBanana API로 각 컷의 이미지 생성
4. **결과 표시**: 생성된 4컷 만화를 사용자에게 제공

## 기술 스택

| 구분 | 기술 |
|------|------|
| Framework | FastAPI |
| Database | SQLite (SQLAlchemy ORM) |
| Template | Jinja2 (HTML 템플릿) |
| Async Task | FastAPI BackgroundTasks |
| Storage | 로컬 파일시스템 (추후 S3 확장 고려) |
| External APIs | Google Gemini API (텍스트 + 이미지 생성) |

## 프로젝트 구조

```
toon-minutes/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config.py            # 설정 관리
│   ├── database.py          # DB 연결 설정
│   ├── models/              # SQLAlchemy 모델
│   │   └── models.py
│   ├── schemas/             # Pydantic 스키마
│   │   └── schemas.py
│   ├── routers/             # API 라우터
│   │   └── comic.py
│   ├── services/            # 비즈니스 로직
│   │   ├── llm_service.py   # Gemini LLM 연동
│   │   ├── image_service.py # NanoBanana API 연동
│   │   └── comic_service.py # 만화 생성 오케스트레이션
│   ├── templates/           # Jinja2 HTML 템플릿
│   │   ├── index.html
│   │   └── result.html
│   └── static/              # CSS, JS, 생성된 이미지
│       ├── css/
│       ├── js/
│       └── images/
├── tests/
├── requirements.txt
└── .env
```

## 핵심 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/` | 메인 페이지 (회의록 입력 폼) |
| POST | `/generate` | 만화 생성 요청 시작 |
| GET | `/result/{task_id}` | 생성 결과 조회 |
| GET | `/status/{task_id}` | 생성 진행 상태 확인 (polling용) |

## 데이터 모델

### Task
생성 작업을 추적하는 모델
```python
class Task(Base):
    id: str              # UUID
    status: str          # pending | processing | completed | failed
    meeting_text: str    # 원본 회의록
    error_message: str   # 실패 시 에러 메시지
    created_at: datetime
    updated_at: datetime
```

### Comic
생성된 만화 정보를 저장하는 모델
```python
class Comic(Base):
    id: str              # UUID
    task_id: str         # FK to Task
    part_number: int     # 만화 파트 번호 (1부터 시작)
    panels_json: str     # 4컷 시나리오 JSON
    image_paths: str     # 생성된 이미지 경로들 (JSON array)
    created_at: datetime
```

## 서비스 레이어 설계

### LLMService
Gemini API를 사용하여 회의록을 분석하고 4컷 시나리오를 생성
- `analyze_meeting(text: str) -> list[PanelScenario]`
- 반환 형식: 각 패널의 설명, 대사, 이미지 프롬프트

### ImageService
Gemini Image(NanoBanana) API를 사용하여 이미지 생성
- `generate_image(prompt: str) -> str` (이미지 경로 반환)
- 모델: `gemini-2.5-flash-preview-04-17`
- 인터페이스 추상화로 다른 이미지 생성 서비스로 교체 가능

### ComicService
전체 만화 생성 플로우를 오케스트레이션
- `create_comic(task_id: str, meeting_text: str) -> Comic`
- 흐름: 회의록 분석 → 이미지 생성 → DB 저장 → 상태 업데이트

## 개발 컨벤션

### Python
- Python 3.11+ 사용
- Type hints 필수
- async/await 패턴 적극 활용
- f-string 포맷팅 사용

### 환경 설정
- 모든 API 키와 설정은 `.env` 파일로 관리
- `python-dotenv`로 환경변수 로드
- 필수 환경변수:
  - `GEMINI_API_KEY` (텍스트 분석 + 이미지 생성 모두 사용)
  - `DATABASE_URL` (기본값: `sqlite+aiosqlite:///./toon_minutes.db`)

### 코드 스타일
- PEP 8 준수
- 함수/메서드에 docstring 작성
- 에러 처리 시 구체적인 예외 타입 사용

## 확장 고려사항

### Storage 추상화
현재 로컬 파일시스템 사용, S3 전환을 위한 인터페이스 설계:
```python
class StorageInterface(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str: ...

    @abstractmethod
    async def get_url(self, filename: str) -> str: ...
```

### 인증 (Auth)
- 현재: 인증 없음
- 추후: API 키 인증 또는 OAuth 추가 가능한 미들웨어 구조

### Email 알림
- 선택적 Gmail 모듈 연동
- 만화 생성 완료 시 이메일 알림 기능

## 로컬 개발 환경

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 서버 실행
uvicorn app.main:app --reload
```

## 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트 파일 실행
pytest tests/test_services.py

# 커버리지 포함
pytest --cov=app
```
