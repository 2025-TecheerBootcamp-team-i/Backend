"""
커스텀 파서: 단순 텍스트와 JSON을 모두 처리
"""
from rest_framework.parsers import JSONParser
from rest_framework.exceptions import ParseError
import json


class FlexibleJSONParser(JSONParser):
    """
    JSON과 단순 텍스트 모두 처리하는 유연한 파서
    
    사용자가 단순 텍스트("여름의 장미")나 JSON({"prompt": "여름의 장미"})을
    모두 전송할 수 있도록 지원합니다.
    """
    
    def parse(self, stream, media_type=None, parser_context=None):
        """
        JSON 형식이면 JSON으로 파싱하고,
        아니면 단순 텍스트를 {"prompt": "텍스트"} 형태로 변환
        """
        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', 'utf-8')
        
        try:
            # 스트림 내용 읽기
            data = stream.read()
            decoded_data = data.decode(encoding).strip()
            
            if not decoded_data:
                # 빈 데이터
                return {}
            
            try:
                # JSON 파싱 시도
                parsed = json.loads(decoded_data)
                return parsed
            except (json.JSONDecodeError, ValueError):
                # JSON이 아니면 단순 텍스트로 처리
                # "여름의 장미" -> {"prompt": "여름의 장미"}
                return {"prompt": decoded_data}
                
        except Exception as exc:
            raise ParseError(f'JSON parse error - {str(exc)}')
