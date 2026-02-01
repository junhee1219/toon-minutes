#!/bin/bash
# GitHub Pages 배포용 파일 복사 스크립트

NGROK_URL="https://morgan-bipectinate-unnicely.ngrok-free.dev"

echo "📁 docs 폴더로 파일 복사 중..."

# 폴더 생성
mkdir -p docs/static/css docs/static/js

# HTML 복사
cp app/templates/index.html docs/
cp app/templates/result.html docs/

# CSS 복사
cp app/static/css/style.css docs/static/css/

# JS 복사 후 API_BASE_URL 변경
cp app/static/js/app.js docs/static/js/
sed -i '' "s|const API_BASE_URL = '';|const API_BASE_URL = '${NGROK_URL}';|g" docs/static/js/app.js

# result.html의 API_BASE_URL도 변경
sed -i '' "s|const API_BASE_URL = '';|const API_BASE_URL = '${NGROK_URL}';|g" docs/result.html

echo "✅ 완료!"
echo ""
echo "📌 ngrok URL 변경 시:"
echo "   이 스크립트 상단의 NGROK_URL 변수를 수정하세요"
echo ""
echo "🚀 GitHub에 push하면 자동 배포됩니다"
