#!/bin/bash
# ngrok URL을 가져오는 유틸리티 스크립트

echo "🔍 ngrok 터널 URL 확인 중..."
echo ""

# ngrok API에서 터널 정보 가져오기
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$NGROK_URL" ]; then
    echo "❌ ngrok이 실행 중이지 않거나 터널이 없습니다."
    echo ""
    echo "다음 명령어로 ngrok을 시작하세요:"
    echo "  docker-compose --profile ngrok up -d ngrok"
    echo ""
    echo "또는 ngrok 웹 UI에서 확인하세요:"
    echo "  http://localhost:4040"
    exit 1
fi

echo "✅ ngrok 터널 URL:"
echo "   $NGROK_URL"
echo ""
echo "📋 .env 파일의 SUNO_CALLBACK_URL에 다음을 설정하세요:"
echo "   SUNO_CALLBACK_URL=${NGROK_URL}/api/v1/webhook/suno/"
echo ""
