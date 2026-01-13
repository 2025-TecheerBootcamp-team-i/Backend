"""
음악 생성 유틸리티 함수
"""


def extract_genre_from_prompt(prompt: str) -> str:
    """
    프롬프트에서 장르 추출 (간단한 파싱)
    
    Args:
        prompt: 영어 프롬프트
        
    Returns:
        추출된 장르 문자열
    """
    prompt_lower = prompt.lower()
    
    # 주요 장르 키워드 매칭
    genre_keywords = {
        'k-pop': 'K-Pop',
        'pop': 'Pop',
        'rock': 'Rock',
        'jazz': 'Jazz',
        'classical': 'Classical',
        'hip-hop': 'Hip-Hop',
        'r&b': 'R&B',
        'electronic': 'Electronic',
        'folk': 'Folk',
        'country': 'Country',
        'ballad': 'Ballad'
    }
    
    for keyword, genre in genre_keywords.items():
        if keyword in prompt_lower:
            return genre
    
    return 'Unknown'
