import json
import logging

from app.database import async_session
from app.models import ApiLog

logger = logging.getLogger(__name__)


async def log_api_call(
    task_id: str | None,
    service: str,
    method: str,
    model: str,
    request_body: dict,
    response_body: dict,
    status: str,
    error_message: str | None,
    duration: float,
    attempt: int = 1,
) -> None:
    """API 호출 로그를 DB에 저장. 로깅 실패가 메인 플로우에 영향 없도록 처리."""
    try:
        async with async_session() as session:
            log = ApiLog(
                task_id=task_id,
                service=service,
                method=method,
                model=model,
                request_body=json.dumps(request_body, ensure_ascii=False, default=str),
                response_body=json.dumps(response_body, ensure_ascii=False, default=str),
                status=status,
                error_message=error_message,
                duration=round(duration, 3),
                attempt=attempt,
            )
            session.add(log)
            await session.commit()
    except Exception as e:
        logger.warning(f"API 로그 저장 실패: {type(e).__name__}: {e}")
