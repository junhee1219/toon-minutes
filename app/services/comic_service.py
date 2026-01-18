import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, Comic
from app.services.llm_service import llm_service
from app.services.image_service import image_service


class ComicService:
    """만화 생성 오케스트레이션 서비스"""

    async def create_comic(self, db: AsyncSession, task_id: str, meeting_text: str) -> None:
        """전체 만화 생성 프로세스 실행"""
        task = await db.get(Task, task_id)
        if not task:
            return

        try:
            # 1. 상태 업데이트
            task.status = "processing"
            await db.commit()

            # 2. LLM으로 시나리오 생성
            panels = await llm_service.analyze_meeting(meeting_text)

            # 3. 각 패널 이미지 생성
            image_paths = []
            for panel in panels:
                path = await image_service.generate_image(panel.image_prompt)
                image_paths.append(path)

            # 4. Comic 저장
            comic = Comic(
                task_id=task_id,
                part_number=1,
                panels_json=json.dumps([p.model_dump() for p in panels], ensure_ascii=False),
                image_paths=json.dumps(image_paths),
            )
            db.add(comic)

            # 5. 완료 상태 업데이트
            task.status = "completed"
            await db.commit()

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            await db.commit()
            raise


comic_service = ComicService()
