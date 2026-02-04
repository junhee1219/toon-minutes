import asyncio
import logging
import urllib.parse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """텔레그램 알림 서비스"""

    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id and settings.env == "prod")

    def send_message(self, text: str) -> None:
        """텔레그램 메시지 전송 (fire-and-forget, 비즈니스 로직에 영향 없음)"""
        if not self.enabled:
            return
        asyncio.create_task(self._do_send(text))

    def notify_server_started(self) -> None:
        """서버 시작 알림"""
        self.send_message("🚀 Toon-Minutes 서버가 시작되었습니다!")

    def notify_health_check(self) -> None:
        """헬스체크 알림"""
        self.send_message("💚 서버 정상 동작 중")

    def notify_task_created(self, nickname: str | None, meeting_text: str) -> None:
        """태스크 생성 알림 (닉네임 + 내용 미리보기)"""
        name = nickname or "익명"
        preview = meeting_text[:10000] + ("..." if len(meeting_text) > 10000 else "")
        self.send_message(f"🆕 새 요청!\n👤 {name}\n📝 {preview}")

    def notify_task_completed(
        self, task_id: str, meeting_text: str, image_urls: list[str], duration: float
    ) -> None:
        """태스크 완료 알림 (원문 + S3 URL)"""
        short_id = task_id[:8]
        preview = meeting_text[:10000] + ("..." if len(meeting_text) > 10000 else "")
        urls = "\n".join(image_urls) if image_urls else "(없음)"
        self.send_message(
            f"✅ 완료 [{short_id}] ({duration:.1f}s)\n"
            f"📝 {preview}\n"
            f"🖼 이미지:\n{urls}"
        )

    def notify_task_failed(self, task_id: str, error: str) -> None:
        """태스크 실패 알림"""
        short_id = task_id[:8]
        self.send_message(f"❌ 실패 [{short_id}]\n{error[:200]}")

    async def _do_send(self, text: str) -> None:
        """실제 HTTP 전송 (내부용)"""
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&text={encoded_text}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    logger.debug(f"텔레그램 알림 전송 성공: {text}")
                else:
                    logger.warning(f"텔레그램 알림 전송 실패: {response.status_code}")
        except Exception as e:
            logger.warning(f"텔레그램 알림 전송 중 오류: {e}")


telegram_service = TelegramService()
