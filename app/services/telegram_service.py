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
        self.enabled = bool(self.bot_token and self.chat_id)

    async def send_message(self, text: str) -> bool:
        """텔레그램 메시지 전송 (실패해도 예외 발생 안함)"""
        if not self.enabled:
            return False

        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&text={encoded_text}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    logger.debug(f"텔레그램 알림 전송 성공: {text}")
                    return True
                else:
                    logger.warning(f"텔레그램 알림 전송 실패: {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"텔레그램 알림 전송 중 오류: {e}")
            return False

    async def notify_task_status(self, task_id: str, status: str, extra: str = "") -> bool:
        """태스크 상태 변경 알림"""
        short_id = task_id[:8]
        emoji = {
            "pending": "🆕",
            "processing": "⏳",
            "completed": "✅",
            "failed": "❌",
        }.get(status, "📌")

        message = f"{emoji} Task [{short_id}] → {status}"
        if extra:
            message += f"\n{extra}"

        return await self.send_message(message)


telegram_service = TelegramService()
