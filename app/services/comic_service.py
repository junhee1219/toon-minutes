import asyncio
import json
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession
from google.genai.errors import ServerError

from app.models import Task, Comic
from app.services.llm_service import llm_service
from app.services.image_service import image_service
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)


def get_friendly_error_message(e: Exception) -> str:
    """에러를 사용자 친화적 메시지로 변환"""
    error_str = str(e).lower()

    if isinstance(e, ServerError) or "503" in error_str or "overloaded" in error_str:
        return "AI 서버가 지금 바빠요. 잠시 후 다시 시도해 주세요!"
    elif "rate limit" in error_str or "429" in error_str:
        return "요청이 너무 많아요. 1분 후에 다시 시도해 주세요."
    elif "timeout" in error_str:
        return "응답 시간이 초과됐어요. 내용을 조금 줄여서 다시 시도해 주세요."
    elif "safety" in error_str:
        return "입력 내용에 문제가 있어요. 다른 내용으로 시도해 주세요."
    else:
        return f"문제가 발생했어요. 잠시 후 다시 시도해 주세요. ({type(e).__name__})"


class ComicService:
    """만화 생성 오케스트레이션 서비스"""

    async def create_comic_from_scenario(
        self,
        db: AsyncSession,
        task_id: str,
        meeting_text: str,
        scenario_task: asyncio.Task,
        images: list[bytes] = None,
    ) -> None:
        """이미 시작된 시나리오 생성 task를 받아서 결과 대기 후 이미지 생성"""
        images = images or []
        task = await db.get(Task, task_id)
        if not task:
            return

        total_start = time.time()
        short_id = task_id[:8]

        try:
            # 1. 상태 업데이트
            logger.info(f"[Task {short_id}] pending → processing")
            task.status = "processing"
            await db.commit()

            telegram_service.send_message(f"⏳ Task [{short_id}] 생성 시작")

            # 2. 시나리오 생성 결과 대기 (이미 시작된 task)
            scenario_start = time.time()
            panels = await scenario_task
            scenario_elapsed = time.time() - scenario_start
            task.scenario_duration = round(scenario_elapsed, 1)
            logger.info(f"[Task {short_id}] 시나리오 생성 완료 ({scenario_elapsed:.1f}s) - {len(panels)}개 에피소드")

            # 3. 에피소드 수에 따라 분기
            if len(panels) >= 2:
                # 캐릭터 시트 방식: 레퍼런스 이미지 생성 후 병렬 처리
                image_paths, sheet_elapsed, episode_elapsed = await self._generate_with_character_sheet(task, panels, short_id)
                task.character_sheet_duration = round(sheet_elapsed, 1)
                task.episode_image_duration = round(episode_elapsed, 1)
            else:
                # 단일 에피소드: 기존 방식
                image_paths, episode_elapsed = await self._generate_single(panels, short_id)
                task.episode_image_duration = round(episode_elapsed, 1)

            # 4. Comic 저장
            comic = Comic(
                task_id=task_id,
                part_number=1,
                panels_json=json.dumps([p.model_dump() for p in panels], ensure_ascii=False),
                image_paths=json.dumps(image_paths),
            )
            db.add(comic)

            # 5. 완료 상태 업데이트
            total_elapsed = time.time() - total_start
            task.total_duration = round(total_elapsed, 1)
            logger.info(f"[Task {short_id}] processing → completed (총 {total_elapsed:.1f}s)")
            task.status = "completed"
            await db.commit()

            telegram_service.notify_task_completed(
                task_id, meeting_text, image_paths, total_elapsed
            )

        except asyncio.CancelledError:
            logger.info(f"[Task {short_id}] 시나리오 생성 취소됨")
            task.status = "failed"
            task.error_message = "입력이 유효하지 않아 생성이 취소되었습니다."
            await db.commit()

        except Exception as e:
            logger.error(f"[Task {short_id}] 만화 생성 실패: {e}")
            task.status = "failed"
            task.error_message = get_friendly_error_message(e)
            await db.commit()

            telegram_service.notify_task_failed(task_id, str(e))

    async def create_comic(
        self,
        db: AsyncSession,
        task_id: str,
        meeting_text: str,
        images: list[bytes] = None,
    ) -> None:
        """전체 만화 생성 프로세스 실행"""
        images = images or []
        task = await db.get(Task, task_id)
        if not task:
            return

        total_start = time.time()
        short_id = task_id[:8]

        try:
            # 1. 상태 업데이트
            logger.info(f"[Task {short_id}] pending → processing")
            task.status = "processing"
            await db.commit()

            telegram_service.send_message(f"⏳ Task [{short_id}] 생성 시작")

            # 2. LLM으로 시나리오 생성 (이미지 포함)
            scenario_start = time.time()
            panels = await llm_service.analyze_meeting(meeting_text, images)
            scenario_elapsed = time.time() - scenario_start
            task.scenario_duration = round(scenario_elapsed, 1)
            logger.info(f"[Task {short_id}] 시나리오 생성 완료 ({scenario_elapsed:.1f}s) - {len(panels)}개 에피소드")

            # 3. 에피소드 수에 따라 분기
            if len(panels) >= 2:
                # 캐릭터 시트 방식: 레퍼런스 이미지 생성 후 병렬 처리
                image_paths, sheet_elapsed, episode_elapsed = await self._generate_with_character_sheet(task, panels, short_id)
                task.character_sheet_duration = round(sheet_elapsed, 1)
                task.episode_image_duration = round(episode_elapsed, 1)
            else:
                # 단일 에피소드: 기존 방식
                image_paths, episode_elapsed = await self._generate_single(panels, short_id)
                task.episode_image_duration = round(episode_elapsed, 1)

            # 4. Comic 저장
            comic = Comic(
                task_id=task_id,
                part_number=1,
                panels_json=json.dumps([p.model_dump() for p in panels], ensure_ascii=False),
                image_paths=json.dumps(image_paths),
            )
            db.add(comic)

            # 5. 완료 상태 업데이트
            total_elapsed = time.time() - total_start
            task.total_duration = round(total_elapsed, 1)
            logger.info(f"[Task {short_id}] processing → completed (총 {total_elapsed:.1f}s)")
            task.status = "completed"
            await db.commit()

            telegram_service.notify_task_completed(
                task_id, meeting_text, image_paths, total_elapsed
            )

        except Exception as e:
            logger.error(f"[Task {short_id}] 만화 생성 실패: {e}")
            task.status = "failed"
            task.error_message = get_friendly_error_message(e)
            await db.commit()

            telegram_service.notify_task_failed(task_id, str(e))

    async def _generate_single(self, panels, short_id: str = "") -> tuple[list[str], float]:
        """단일 에피소드 이미지 생성 (기존 방식)"""
        image_start = time.time()
        base_style_prompt = "Masterpiece, best quality, 2D Webtoon style, bold black outlines, flat colors, comic book layout, vibrant pastel tones. "
        async def generate_with_index(index: int, prompt: str):
            path = await image_service.generate_image(base_style_prompt + prompt)
            return index, path

        tasks = [
            generate_with_index(i, panel.image_prompt)
            for i, panel in enumerate(panels)
        ]
        results = await asyncio.gather(*tasks)

        image_elapsed = time.time() - image_start
        logger.info(f"[Task {short_id}] 에피소드 이미지 생성 완료 ({image_elapsed:.1f}s) - {len(panels)}장")

        paths = [path for _, path in sorted(results, key=lambda x: x[0])]
        return paths, image_elapsed

    async def _generate_with_character_sheet(self, task: Task, panels, short_id: str = "") -> tuple[list[str], float, float]:
        """캐릭터 시트를 먼저 생성하고, 이를 레퍼런스로 에피소드 이미지 생성"""
        # 1. 캐릭터 시트 프롬프트 직접 구성 (인물 정보만 추출)
        logger.info(f"[Task {short_id}] 캐릭터 시트 프롬프트 구성 중...")
        all_prompts = "\n\n".join([
            f"Episode {p.episode_number}:\n{p.image_prompt}"
            for p in panels
        ])

        character_sheet_prompt = f"""
Create a CHARACTER DESIGN SHEET (Turnaround view) for the main characters.
**IMPORTANT:** Ignore all actions (running, eating, sitting) described below. Focus ONLY on the character's design, clothing, and features.

**Composition:**
- Draw the main characters standing side-by-side in a neutral pose (Front view).
- Background matching the story's world setting, no text, no speech bubbles.
- Style: 2D Webtoon style, flat color, bold outlines, SD(Super Deformed) ratio.

**Context from story (Extract character details from here):**

{all_prompts}""".strip()

        logger.info(f"[Task {short_id}] 캐릭터 시트 프롬프트: {character_sheet_prompt[:200]}...")

        # 2. 캐릭터 시트 이미지 생성 (flash 모델 사용)
        sheet_start = time.time()
        character_sheet_url = await image_service.generate_image_fast(character_sheet_prompt)
        sheet_elapsed = time.time() - sheet_start
        logger.info(f"[Task {short_id}] 캐릭터 시트 생성 완료 ({sheet_elapsed:.1f}s)")

        # 3. Task에 캐릭터 시트 URL 저장
        task.character_sheet_url = character_sheet_url

        # 4. 캐릭터 시트를 레퍼런스로 모든 에피소드 이미지 병렬 생성
        logger.info(f"[Task {short_id}] 레퍼런스 기반 {len(panels)}개 에피소드 이미지 생성 중...")
        episode_start = time.time()

        async def generate_with_reference_index(index: int, prompt: str):
            path = await image_service.generate_image_with_reference(prompt, character_sheet_url)
            return index, path

        tasks = [
            generate_with_reference_index(i, panel.image_prompt)
            for i, panel in enumerate(panels)
        ]
        results = await asyncio.gather(*tasks)

        episode_elapsed = time.time() - episode_start
        logger.info(f"[Task {short_id}] 에피소드 이미지 생성 완료 ({episode_elapsed:.1f}s) - {len(panels)}장")

        paths = [path for _, path in sorted(results, key=lambda x: x[0])]
        return paths, sheet_elapsed, episode_elapsed


comic_service = ComicService()
