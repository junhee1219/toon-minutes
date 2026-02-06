# iOS 이미지 붙여넣기 오류 수정안

## 증상
- iPhone에서 사진첩의 JPEG 이미지를 복사 후 contenteditable div에 붙여넣기
- 텍스트도 함께 입력
- **"The String did not match expected pattern"** 에러 발생
- **간헐적**: 같은 방식(사진첩 복사 → 붙여넣기)인데 어떨 땐 되고 어떨 땐 안 됨

## 원인 분석

### 핵심: `innerHTML` → `DOMParser` 라운드트립에서의 데이터 손상

현재 `extractContent()` (app.js:166)의 흐름:

```javascript
const html = meetingInput.innerHTML;                        // 1. 라이브 DOM → HTML 문자열 직렬화
const doc = parser.parseFromString(html, 'text/html');      // 2. HTML 문자열 → 새 DOM 파싱
const imgs = doc.querySelectorAll('img');                    // 3. 새 DOM에서 img 추출
// → img.src를 fetch()로 blob 변환
```

**이 라운드트립이 간헐적 실패의 원인:**

1. **`innerHTML` 직렬화 시 data: URL 손상**
   - iOS Safari가 사진첩 이미지를 `data:image/jpeg;base64,...` (수 MB)로 삽입
   - `innerHTML` getter가 이 거대한 data URL을 HTML 문자열로 직렬화할 때 잘리거나 인코딩이 깨질 수 있음
   - 깨진 data URL → `fetch()` 호출 시 `TypeError: The string did not match the expected pattern`

2. **`blob:` URL의 컨텍스트 분리**
   - iOS Safari가 `blob:https://toonify.kr/uuid` 형태로 삽입하는 경우
   - `innerHTML` → `DOMParser` 과정에서 새 Document가 생성됨
   - 새 Document의 `img.src`에서 blob URL을 읽어도, 원래 페이지 컨텍스트의 blob 참조가 아닐 수 있음
   - `fetch(blobUrl)` 실패

3. **간헐적인 이유**
   - 이미지 크기에 따라 다름: 작은 스크린샷은 성공, 큰 사진은 실패
   - 이미지 포맷에 따라 다름: 단순 JPEG은 성공, HEIC→JPEG 변환된 건 실패
   - iOS 메모리 상태에 따라 다름: 여유 있으면 성공, 부족하면 직렬화 실패

### try-catch로 잡히는데 왜 에러가 보이나?

`extractContent()` 안의 try-catch는 **개별 이미지 추출 실패만 잡음**. 이미지가 유실되더라도 함수 자체는 정상 반환.

하지만 에러가 사용자에게 보인다면, try-catch 밖에서 에러가 발생하는 경우가 있음:
- `meetingInput.innerHTML` 접근 자체가 iOS에서 간헐적으로 실패
- `DOMParser.parseFromString()` 에서 malformed HTML로 예외
- 또는 이미지는 유실되었지만 텍스트도 비어있어서 `내용을 입력해주세요` 대신 다른 에러 경로

## 수정안

### 1. DOMParser 제거 - 라이브 DOM 직접 쿼리 (가장 중요)

불필요한 `innerHTML → DOMParser` 라운드트립을 제거하고 라이브 DOM에서 직접 img 태그를 읽음:

```javascript
async function extractContent() {
    const text = meetingInput.innerText.trim();

    const images = [];
    const imageUrls = [];

    // 라이브 DOM에서 직접 img 태그 쿼리 (DOMParser 라운드트립 제거)
    const imgs = meetingInput.querySelectorAll('img');

    for (const img of imgs) {
        const src = img.src;
        if (!src) continue;

        // 접근 불가능한 스킴 무시
        if (src.startsWith('webkit-fake-url:')) continue;

        try {
            if (src.startsWith('data:')) {
                const response = await fetch(src);
                const blob = await response.blob();
                images.push({ blob, previewUrl: src });
            } else if (src.startsWith('blob:')) {
                const response = await fetch(src);
                const blob = await response.blob();
                images.push({ blob, previewUrl: src });
            } else if (src.startsWith('http://') || src.startsWith('https://')) {
                imageUrls.push({ url: src, previewUrl: src });
            }
        } catch (e) {
            console.warn('이미지 추출 실패 (무시):', src.substring(0, 50), e.message);
        }
    }

    return { text, images, imageUrls };
}
```

**변경 핵심**:
- `meetingInput.innerHTML` + `DOMParser` + `doc.querySelectorAll('img')` → `meetingInput.querySelectorAll('img')`
- 라이브 DOM의 img 요소는 원래 blob/data 참조를 유지하므로 `img.src`가 더 안정적
- 3줄 삭제, 1줄 변경으로 끝

### 2. paste 이벤트 핸들러 추가 (보험)

iOS Safari의 기본 paste 동작 대신 `clipboardData.files`에서 직접 이미지를 추출하여 안전한 data: URL로 삽입:

```javascript
meetingInput.addEventListener('paste', (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
        if (item.type.startsWith('image/')) {
            e.preventDefault();

            const file = item.getAsFile();
            if (!file) continue;

            const reader = new FileReader();
            reader.onload = (event) => {
                const img = document.createElement('img');
                img.src = event.target.result;  // JS가 직접 만든 data: URL
                img.style.maxWidth = '200px';
                img.style.maxHeight = '200px';

                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    range.deleteContents();
                    range.insertNode(img);
                    range.collapse(false);
                } else {
                    meetingInput.appendChild(img);
                }
            };
            reader.readAsDataURL(file);
        }
    }
});
```

**포인트**: Safari가 만드는 불안정한 blob/data URL 대신, JS에서 직접 `FileReader.readAsDataURL()`로 안전한 data: URL을 생성. 이미지 src가 항상 예측 가능한 형태.

### 3. 에러 메시지 개선

```javascript
} catch (error) {
    cleanup();
    showForm();
    const msg = error.message?.includes('pattern')
        ? '이미지 처리 중 문제가 발생했어요. 이미지를 빼고 텍스트만 보내보세요!'
        : error.message;
    showError(msg);
}
```

## 수정 우선순위

| 순위 | 수정 | 효과 | 난이도 |
|------|------|------|--------|
| 1 | DOMParser 제거, 라이브 DOM 쿼리 | 근본 원인 해결 | 3줄 변경 |
| 2 | paste 이벤트 핸들러 | 이미지 src 자체를 안정화 | ~20줄 추가 |
| 3 | 에러 메시지 개선 | UX 개선 | ~3줄 변경 |

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `app/static/js/app.js` | `extractContent()`: DOMParser 제거, 라이브 DOM 쿼리 |
| `app/static/js/app.js` | paste 이벤트 핸들러 추가 |
| `app/static/js/app.js` | 에러 메시지 사용자 친화적 변환 |

## 검증 방법
1. iPhone 실기에서 사진첩의 **큰 사진**(고해상도)을 복사 → 붙여넣기 → 텍스트 입력 → 전송
2. **작은 스크린샷**으로도 같은 테스트 반복
3. 여러 번 반복하여 간헐적 실패가 사라졌는지 확인
4. Safari 개발자 도구에서 console.warn 확인 (이미지 추출 실패가 있는지)
