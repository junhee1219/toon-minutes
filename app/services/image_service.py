from abc import ABC, abstractmethod

import httpx

from app.config import settings


class ImageServiceInterface(ABC):
    """이미지 생성 서비스 인터페이스"""

    @abstractmethod
    async def generate_image(self, prompt: str) -> str:
        """프롬프트로 이미지를 생성하고 저장된 경로 반환"""
        pass


class NanoBananaImageService(ImageServiceInterface):
    """NanoBanana API를 사용한 이미지 생성 서비스"""

    def __init__(self):
        self.api_key = settings.nanobanana_api_key

    async def generate_image(self, prompt: str) -> str:
        """NanoBanana API로 이미지 생성"""
        # TODO: NanoBanana API 연동 구현
        raise NotImplementedError("NanoBanana API 연동 구현 필요")


image_service = NanoBananaImageService()
