# Toon-Minutes 개발 TODO

## 1. 환경 설정
- [ ] `.env` 파일 생성 (`.env.example` 참고)
- [ ] Gemini API 키 발급 및 설정
- [ ] NanoBanana API 키 발급 및 설정
- [ ] 의존성 설치 (`pip install -r requirements.txt`)

## 2. LLM 서비스 구현 (`app/services/llm_service.py`)
- [ ] Gemini API 연동
- [ ] 회의록 분석 프롬프트 작성
- [ ] 4컷 시나리오 JSON 파싱 로직
- [ ] 에러 핸들링

## 3. 이미지 서비스 구현 (`app/services/image_service.py`)
- [ ] NanoBanana API 연동
- [ ] 이미지 생성 요청 로직
- [ ] 이미지 다운로드 및 로컬 저장
- [ ] 에러 핸들링

## 4. 테스트
- [ ] `tests/` 디렉토리 구조 생성
- [ ] 서비스 레이어 단위 테스트
- [ ] API 엔드포인트 통합 테스트
- [ ] E2E 테스트

## 5. 기능 개선 (선택)
- [ ] 회의록 입력 유효성 검사 강화
- [ ] 생성 진행률 표시 (WebSocket 또는 SSE)
- [ ] 이미지 캐싱
- [ ] 결과 히스토리 조회 기능

## 6. 배포 준비 (선택)
- [ ] Dockerfile 작성
- [ ] docker-compose.yml 작성
- [ ] S3 스토리지 연동 (StorageInterface 구현)
- [ ] 프로덕션 설정 분리

## 7. 문서화 (선택)
- [ ] API 문서 보완 (OpenAPI/Swagger)
- [ ] 사용자 가이드 작성
