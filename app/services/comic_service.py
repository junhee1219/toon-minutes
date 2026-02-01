import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, Comic
from app.services.llm_service import llm_service
from app.services.image_service import image_service

logger = logging.getLogger(__name__)


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
            logger.info(f"시나리오 생성 완료: {len(panels)}개 에피소드")

            # 3. 에피소드 수에 따라 분기
            if len(panels) >= 2:
                # 캐릭터 시트 방식: 레퍼런스 이미지 생성 후 병렬 처리
                image_paths = await self._generate_with_character_sheet(task, panels)
            else:
                # 단일 에피소드: 기존 방식
                image_paths = await self._generate_single(panels)

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

    async def _generate_single(self, panels) -> list[str]:
        """단일 에피소드 이미지 생성 (기존 방식)"""
        async def generate_with_index(index: int, prompt: str):
            path = await image_service.generate_image(prompt)
            return index, path

        tasks = [
            generate_with_index(i, panel.image_prompt)
            for i, panel in enumerate(panels)
        ]
        results = await asyncio.gather(*tasks)

        return [path for _, path in sorted(results, key=lambda x: x[0])]

    async def _generate_with_character_sheet(self, task: Task, panels) -> list[str]:
        """캐릭터 시트를 먼저 생성하고, 이를 레퍼런스로 에피소드 이미지 생성"""
        # 1. 캐릭터 시트 프롬프트 직접 구성
        logger.info("캐릭터 시트 프롬프트 구성 중...")
        all_prompts = "\n\n".join([
            f"Episode {p.episode_number}:\n{p.image_prompt}"
            for p in panels
        ])

        character_sheet_prompt = f"""Based on the following episode descriptions, create a CHARACTER SHEET image that includes:
1. ALL main characters appearing across all episodes, standing together
2. The overall art style, color tone, and atmosphere for this comic series
3. A representative background that matches the world/setting

Episode descriptions:
{all_prompts}

Style: 2D Webtoon, bold black outlines, flat colors, SD/Chibi style (2-head ratio), clean and expressive.
This image will be used as a style reference for all subsequent episode illustrations."""

        logger.info(f"캐릭터 시트 프롬프트: {character_sheet_prompt[:200]}...")

        # 2. 캐릭터 시트 이미지 생성
        logger.info("캐릭터 시트 이미지 생성 중...")
        character_sheet_url = await image_service.generate_image(character_sheet_prompt)
        logger.info(f"캐릭터 시트 생성 완료: {character_sheet_url}")

        # 3. Task에 캐릭터 시트 URL 저장
        task.character_sheet_url = character_sheet_url

        # 4. 캐릭터 시트를 레퍼런스로 모든 에피소드 이미지 병렬 생성
        logger.info(f"레퍼런스 기반 {len(panels)}개 에피소드 이미지 생성 중...")

        async def generate_with_reference_index(index: int, prompt: str):
            path = await image_service.generate_image_with_reference(prompt, character_sheet_url)
            return index, path

        tasks = [
            generate_with_reference_index(i, panel.image_prompt)
            for i, panel in enumerate(panels)
        ]
        results = await asyncio.gather(*tasks)

        return [path for _, path in sorted(results, key=lambda x: x[0])]


comic_service = ComicService()
