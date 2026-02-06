# 전역 예외 처리 (AOP 스타일) 구현 현황

## 개요
예외 발생 시 stacktrace 로깅 + 텔레그램 알림을 각 메서드마다 산발적으로 넣는 대신, 전역 2곳에서 처리.

## 구조

```
[HTTP 요청]
    └→ FastAPI global_exception_handler (main.py)
        - 모든 미처리 HTTP 예외 캐치
        - logger.exception() + telegram 알림
        - 500 응답 반환

[백그라운드 태스크]
    └→ comic_service.py except 블록
        - create_comic / create_comic_from_scenario의 except
        - logger.exception() + telegram.notify_task_failed()
        - 하위 서비스(llm, image)의 예외가 여기로 버블업
```

## 예외 전파 흐름

```
image_service._generate_with_retry()  → raise (logger.error만)
    ↑
image_service.generate_image()         → raise (그대로 전파)
    ↑
comic_service.create_comic()           → except: logger.exception() + telegram ✅
```

```
llm_service._generate_with_retry()     → raise (logger.error만)
    ↑
llm_service.analyze_meeting()          → raise (그대로 전파)
    ↑
comic_service.create_comic()           → except: logger.exception() + telegram ✅
```

```
llm_service.validate_input()           → raise
    ↑
router (HTTP request context)          → global_exception_handler ✅
```

## 이미 적용된 변경사항

### `app/main.py` - 전역 HTTP 예외 핸들러 추가
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception(f"Unhandled exception: {request.method} {request.url.path}")
    telegram_service.notify_exception(
        "http", f"{request.method} {request.url.path}",
        traceback.format_exc(),
    )
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다."})
```

### `app/services/telegram_service.py` - notify_exception 메서드 추가
```python
def notify_exception(self, service, method, error, task_id=None):
    """예외 발생 알림"""
    tid = f"[{task_id[:8]}] " if task_id else ""
    self.send_message(f"🔥 예외 {tid}{service}.{method}\n{error[:500]}")
```

### `app/services/comic_service.py` - logger.error → logger.exception
기존 `logger.error()` → `logger.exception()` 변경 (stacktrace 포함)

### `app/services/llm_service.py` / `image_service.py`
- 하위 서비스에서는 `logger.error()`만 (stacktrace/telegram 없음)
- 예외는 상위로 전파되어 comic_service 또는 global_exception_handler에서 처리

## 텔레그램 알림 예시
```
🔥 예외 [a1b2c3d4] image.generate_image
Traceback (most recent call last):
  File "image_service.py", line 60, in _generate_with_retry
    ...
google.api_core.exceptions.InternalServerError: 503
```
