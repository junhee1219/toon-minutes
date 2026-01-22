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

    // 기본 대기 메시지
    const defaultMessages = [
        "회의의 핵심 내용을 파악하고 있어요",
        "등장인물들을 분석하고 있어요",
        "재미있는 장면을 구상하고 있어요",
        "4컷 스토리를 만들고 있어요",
        "각 장면의 대사를 다듬고 있어요",
        "캐릭터의 표정을 그리고 있어요",
        "배경을 채색하고 있어요",
        "마지막 터치를 하고 있어요",
    ];

    // 팁 메시지
    const tips = [
        "만화 생성에는 보통 1-2분 정도 소요됩니다",
        "회의록이 길수록 더 재미있는 만화가 나와요",
        "생성된 만화는 다운로드할 수 있어요",
        "여러 사람이 등장하면 더 다채로운 만화가 됩니다",
    ];

    // 회의록에서 의미있는 문장 추출
    function extractMessagesFromMeeting(text) {
        const lines = text.split('\n').filter(line => line.trim());
        const messages = [];

        for (const line of lines) {
            // 발화자: 내용 형식에서 내용 추출
            const match = line.match(/[^:：]+[:：]\s*(.+)/);
            if (match && match[1]) {
                const content = match[1].trim();
                if (content.length > 5 && content.length < 50) {
                    messages.push(`"${content}"`);
                }
            } else if (line.trim().length > 10 && line.trim().length < 60) {
                // 일반 문장
                messages.push(line.trim());
            }
        }

        // 최대 10개까지, 중복 제거
        const uniqueMessages = [...new Set(messages)].slice(0, 10);

        // 추출된 메시지를 기반으로 대기 문구 생성
        return uniqueMessages.map(msg => {
            const templates = [
                `${msg} 라고 했군요...`,
                `${msg} 를 만화로 표현하는 중...`,
                `${msg} 장면을 그리고 있어요`,
            ];
            return templates[Math.floor(Math.random() * templates.length)];
        });
    }

    // 메시지 로테이션 시작
    function startMessageRotation(meetingText) {
        const meetingMessages = extractMessagesFromMeeting(meetingText);
        const allMessages = [...meetingMessages, ...defaultMessages];
        let messageIndex = 0;

        // 초기 메시지
        rotatingMessage.textContent = allMessages[0] || defaultMessages[0];

        messageRotationInterval = setInterval(() => {
            // 페이드 아웃
            rotatingMessage.classList.add('fade-out');

            setTimeout(() => {
                messageIndex = (messageIndex + 1) % allMessages.length;
                rotatingMessage.textContent = allMessages[messageIndex];
                rotatingMessage.classList.remove('fade-out');
            }, 500);
        }, 5000);
    }

    // 팁 로테이션
    function startTipRotation() {
        let tipIndex = 0;
        setInterval(() => {
            tipIndex = (tipIndex + 1) % tips.length;
            tipText.textContent = tips[tipIndex];
        }, 8000);
    }

    // 프로그레스바 업데이트
    function updateProgress(percent, status) {
        currentProgress = percent;
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        if (status) {
            progressStatus.textContent = status;
        }
    }

    // 가짜 프로그레스 시뮬레이션 (실제 진행률을 모르므로)
    function simulateProgress() {
        const stages = [
            { target: 15, status: '회의록 분석 중...' },
            { target: 30, status: '스토리 구성 중...' },
            { target: 50, status: '1번째 컷 생성 중...' },
            { target: 65, status: '2번째 컷 생성 중...' },
            { target: 80, status: '3번째 컷 생성 중...' },
            { target: 90, status: '4번째 컷 생성 중...' },
        ];

        let stageIndex = 0;

        progressInterval = setInterval(() => {
            if (stageIndex < stages.length && currentProgress < stages[stageIndex].target) {
                const increment = Math.random() * 2 + 0.5;
                const newProgress = Math.min(currentProgress + increment, stages[stageIndex].target);
                updateProgress(Math.floor(newProgress), stages[stageIndex].status);

                if (newProgress >= stages[stageIndex].target) {
                    stageIndex++;
                }
            }
        }, 1000);
    }

    // UI 상태 전환
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

    // 정리
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

    // 폼 제출 핸들러
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const meetingText = document.getElementById('meeting-text').value;

        cleanup();
        currentProgress = 0;
        updateProgress(0, '준비 중...');
        showLoading();
        startMessageRotation(meetingText);
        startTipRotation();
        simulateProgress();

        try {
            // 만화 생성 요청
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ meeting_text: meetingText }),
            });

            if (!response.ok) {
                throw new Error('생성 요청에 실패했습니다');
            }

            const task = await response.json();

            // 상태 폴링
            await pollStatus(task.id);

        } catch (error) {
            cleanup();
            showForm();
            showError(error.message);
        }
    });

    // 상태 폴링
    async function pollStatus(taskId) {
        const maxAttempts = 120; // 4분
        let attempts = 0;

        while (attempts < maxAttempts) {
            try {
                const response = await fetch(`/status/${taskId}`);
                const status = await response.json();

                if (status.status === 'completed') {
                    updateProgress(100, '완료!');
                    cleanup();

                    // 잠시 대기 후 결과 페이지로 이동
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
