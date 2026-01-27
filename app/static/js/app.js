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

    let messageRotationInterval = null;
    let progressInterval = null;
    let currentProgress = 0;
    let visitorId = null;

    // FingerprintJS 초기화
    if (window.FingerprintJS) {
        FingerprintJS.load().then(fp => fp.get()).then(result => {
            visitorId = result.visitorId;
        });
    }

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

    // 메시지 로테이션 (서버에서 받은 메시지 사용)
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

        const interval = Math.random() * 1000 + 2000; // 2~3초
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

        const meetingText = document.getElementById('meeting-text').value;
        const submitBtn = form.querySelector('button');
        const originalBtnText = submitBtn.textContent;

        submitBtn.disabled = true;
        submitBtn.textContent = '🤔 내용 파악하는 중...';
        errorSection.classList.add('hidden');

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ meeting_text: meetingText, fingerprint: visitorId }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '생성 요청에 실패했습니다');
            }

            const data = await response.json();
            const taskId = data.task.id;
            const messages = data.messages || [];

            // 검증 통과 → 로딩 UI 시작
            cleanup();
            currentProgress = 0;
            updateProgress(0, '준비 중...');
            showLoading();
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
                const response = await fetch(`/status/${taskId}`);
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
