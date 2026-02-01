// API 서버 URL (GitHub Pages 배포 시 ngrok URL로 변경)
const API_BASE_URL = '';  // 로컬: '', 배포: 'https://xxxx.ngrok-free.app'

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const formSection = document.getElementById('form-section');
    const loadingSection = document.getElementById('loading-section');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const rotatingMessage = document.getElementById('rotating-message');
    const progressFill = document.getElementById('progress-fill');
    const progressStatus = document.getElementById('progress-status');
    const progressPercent = document.getElementById('progress-percent');
    const tipText = document.getElementById('tip-text');
    const meetingInput = document.getElementById('meeting-input');

    // 모바일 최적화: 입력 영역 터치 이벤트
    meetingInput.addEventListener('touchstart', () => {
        meetingInput.style.fontSize = '16px'; // 모바일 자동 확대 방지
    });

    meetingInput.addEventListener('blur', () => {
        meetingInput.style.fontSize = '14px';
    });

    let messageRotationInterval = null;
    let progressInterval = null;
    let currentProgress = 0;
    let visitorId = localStorage.getItem('visitor_id');
    let nickname = null;
    const greeting = document.getElementById('greeting');

    // 방문자 초기화
    (async () => {
        try {
            const url = visitorId ? `${API_BASE_URL}/visitor?id=${visitorId}` : `${API_BASE_URL}/visitor`;
            const res = await fetch(url, { method: 'POST' });
            const data = await res.json();

            if (data.id) {
                visitorId = data.id;
                localStorage.setItem('visitor_id', data.id);
            }
            if (data.nickname) {
                nickname = data.nickname;
                greeting.textContent = `${nickname}님, 어서오세요`;
                greeting.classList.remove('hidden');
            }
        } catch (e) { /* 실패해도 무시 */ }
    })();

    const fallbackMessages = [
        "만화 컷을 구성하고 있어요",
        "캐릭터를 그리는 중이에요",
        "배경을 채색하고 있어요",
        "대사를 배치하고 있어요",
        "거의 다 됐어요, 조금만 기다려주세요",
    ];

    const tips = [
        "만화 생성에는 1-2분 정도 소요됩니다",
        "생성된 만화는 다운로드할 수 있어요",
        "회의록이 길면 여러 에피소드로 나뉠 수 있어요",
    ];

    // contenteditable에서 텍스트와 이미지 추출
    async function extractContent() {
        const html = meetingInput.innerHTML;
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // 텍스트 추출 (줄바꿈 유지)
        const text = meetingInput.innerText.trim();

        // 이미지 추출
        const images = [];
        const imgs = doc.querySelectorAll('img');

        for (const img of imgs) {
            const src = img.src;
            if (!src) continue;

            try {
                let blob;
                if (src.startsWith('data:')) {
                    // base64 → blob
                    const response = await fetch(src);
                    blob = await response.blob();
                } else if (src.startsWith('blob:')) {
                    // blob URL → blob
                    const response = await fetch(src);
                    blob = await response.blob();
                } else {
                    // 외부 URL은 스킵 (CORS)
                    continue;
                }
                images.push(blob);
            } catch (e) {
                console.error('이미지 추출 실패:', e);
            }
        }

        return { text, images };
    }

    // 메시지 로테이션
    function startMessageRotation(messages) {
        const allMessages = messages.length > 0 ? messages : fallbackMessages;
        let usedIndices = new Set();

        function getRandomMessage() {
            if (usedIndices.size >= allMessages.length) {
                usedIndices.clear();
            }
            let idx;
            do {
                idx = Math.floor(Math.random() * allMessages.length);
            } while (usedIndices.has(idx));
            usedIndices.add(idx);
            return allMessages[idx];
        }

        rotatingMessage.textContent = getRandomMessage();

        const interval = Math.random() * 1000 + 2000;
        messageRotationInterval = setInterval(() => {
            rotatingMessage.classList.add('fade-out');
            setTimeout(() => {
                rotatingMessage.textContent = getRandomMessage();
                rotatingMessage.classList.remove('fade-out');
            }, 300);
        }, interval);
    }

    function startTipRotation() {
        let tipIndex = 0;
        setInterval(() => {
            tipIndex = (tipIndex + 1) % tips.length;
            tipText.textContent = tips[tipIndex];
        }, 8000);
    }

    function updateProgress(percent, status) {
        currentProgress = percent;
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        if (status) {
            progressStatus.textContent = status;
        }
    }

    function simulateProgress() {
        const stages = [
            { target: 20, status: '회의록 분석 중...' },
            { target: 40, status: '스토리 구성 중...' },
            { target: 55, status: '1번째 컷 생성 중...' },
            { target: 70, status: '2번째 컷 생성 중...' },
            { target: 82, status: '3번째 컷 생성 중...' },
            { target: 92, status: '4번째 컷 생성 중...' },
        ];

        let stageIndex = 0;

        progressInterval = setInterval(() => {
            if (stageIndex < stages.length && currentProgress < stages[stageIndex].target) {
                const increment = Math.random() * 1.5 + 0.3;
                const newProgress = Math.min(currentProgress + increment, stages[stageIndex].target);
                updateProgress(Math.floor(newProgress), stages[stageIndex].status);

                if (newProgress >= stages[stageIndex].target) {
                    stageIndex++;
                }
            }
        }, 1000);
    }

    function showLoading() {
        formSection.classList.add('hidden');
        loadingSection.classList.remove('hidden');
        errorSection.classList.add('hidden');
    }

    function showForm() {
        formSection.classList.remove('hidden');
        loadingSection.classList.add('hidden');
    }

    function showError(message) {
        errorSection.classList.remove('hidden');
        errorMessage.textContent = message;
    }

    function cleanup() {
        if (messageRotationInterval) {
            clearInterval(messageRotationInterval);
            messageRotationInterval = null;
        }
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button');
        const originalBtnText = submitBtn.textContent;

        submitBtn.disabled = true;
        submitBtn.textContent = '🤔 내용 파악하는 중...';
        errorSection.classList.add('hidden');

        try {
            // contenteditable에서 텍스트와 이미지 추출
            const { text, images } = await extractContent();

            if (!text) {
                throw new Error('내용을 입력해주세요.');
            }

            let response;

            if (images.length > 0) {
                // 이미지가 있으면 FormData로 전송
                const formData = new FormData();
                formData.append('meeting_text', text);
                if (visitorId) formData.append('visitor_id', visitorId);

                images.forEach((blob, i) => {
                    formData.append('images', blob, `image_${i}.png`);
                });

                response = await fetch(`${API_BASE_URL}/generate-with-images`, {
                    method: 'POST',
                    body: formData,
                });
            } else {
                // 텍스트만 있으면 JSON으로 전송
                response = await fetch(`${API_BASE_URL}/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ meeting_text: text, visitor_id: visitorId }),
                });
            }

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '생성 요청에 실패했습니다');
            }

            const data = await response.json();
            const taskId = data.task.id;
            const messages = data.messages || [];
            if (data.nickname) nickname = data.nickname;

            // 검증 통과 → 로딩 UI 시작
            cleanup();
            currentProgress = 0;
            updateProgress(0, '준비 중...');
            showLoading();

            const badge = document.getElementById('status-badge');
            badge.textContent = nickname ? `${nickname}님의 만화 생성 중` : '생성 중';

            startMessageRotation(messages);
            startTipRotation();
            simulateProgress();

            await pollStatus(taskId);

        } catch (error) {
            cleanup();
            showForm();
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
        }
    });

    async function pollStatus(taskId) {
        const maxAttempts = 120;
        let attempts = 0;

        while (attempts < maxAttempts) {
            try {
                const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
                const status = await response.json();

                if (status.status === 'completed') {
                    updateProgress(100, '완료!');
                    cleanup();
                    setTimeout(() => {
                        window.location.href = `/view/${taskId}`;
                    }, 500);
                    return;
                }

                if (status.status === 'failed') {
                    cleanup();
                    showForm();
                    showError(status.error_message || '만화 생성에 실패했습니다');
                    return;
                }

                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;

            } catch (error) {
                cleanup();
                showForm();
                showError('상태 확인 중 오류가 발생했습니다');
                return;
            }
        }

        cleanup();
        showForm();
        showError('시간이 초과되었습니다. 다시 시도해주세요.');
    }
});
