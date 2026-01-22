document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const statusDiv = document.getElementById('status');
    const statusText = document.getElementById('status-text');
    const resultDiv = document.getElementById('result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const meetingText = document.getElementById('meeting-text').value;
        const submitBtn = form.querySelector('button');

        submitBtn.disabled = true;
        statusDiv.classList.remove('hidden');
        statusText.textContent = '요청 중...';

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
                throw new Error('생성 요청 실패');
            }

            const task = await response.json();

            // 상태 폴링
            await pollStatus(task.id);

        } catch (error) {
            statusText.textContent = '오류: ' + error.message;
        } finally {
            submitBtn.disabled = false;
        }
    });

    async function pollStatus(taskId) {
        const maxAttempts = 60;
        let attempts = 0;

        while (attempts < maxAttempts) {
            const response = await fetch(`/status/${taskId}`);
            const status = await response.json();

            statusText.textContent = getStatusMessage(status.status);

            if (status.status === 'completed') {
                window.location.href = `/view/${taskId}`;
                return;
            }

            if (status.status === 'failed') {
                statusText.textContent = '실패: ' + (status.error_message || '알 수 없는 오류');
                return;
            }

            await new Promise(resolve => setTimeout(resolve, 2000));
            attempts++;
        }

        statusText.textContent = '시간 초과';
    }

    function getStatusMessage(status) {
        const messages = {
            'pending': '대기 중...',
            'processing': '만화 생성 중...',
            'completed': '완료!',
            'failed': '실패',
        };
        return messages[status] || status;
    }
});
