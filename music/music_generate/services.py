"""
음악 생성 서비스
- LlamaService: 한국어 프롬프트를 영어로 변환
- SunoAPIService: Suno API를 통한 음악 생성
"""
import os
import re
import json
import requests
import time
from typing import Dict, Optional

from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .exceptions import SunoAPIError, SunoCreditInsufficientError, SunoAuthenticationError


class LlamaService:
    """
    Tailscale을 통해 Windows Llama와 연결하여 프롬프트 변환을 처리하는 서비스
    """
    
    def __init__(self):
        self.llama_ip = os.getenv('WINDOWS_LLAMA_IP', '100.92.0.45')
        self.model_name = os.getenv('LLAMA_MODEL_NAME', 'llama3.1:8b-instruct-q8_0')
        self.llm = None
        self._setup_llm()
    
    def _setup_llm(self):
        """LangChain LLM 설정"""
        try:
            self.llm = ChatOllama(
                base_url=f"http://{self.llama_ip}:11434",
                model=self.model_name,
                temperature=0.1
            )
        except Exception as e:
            print(f"Llama 연결 실패: {e}")
            self.llm = None
    
    def generate_music_params(self, korean_input: str) -> Optional[Dict]:
        """
        한국어 입력을 Suno API용 파라미터로 변환
        
        Args:
            korean_input: 사용자가 입력한 한국어 프롬프트 (예: "여름의 장미")
            
        Returns:
            {
                'title': '영어 제목',
                'style': '장르',
                'prompt': '음악 설명 프롬프트'
            }
        """
        if not self.llm:
            raise Exception("Llama 연결이 설정되지 않았습니다.")
        
        # Suno API용 구조화된 출력을 위한 프롬프트
        # 중괄호는 LangChain 변수로 인식되므로 이스케이프 필요: {{ }}
        system_prompt_text = """You are a music prompt engineer. Convert Korean input to Suno API parameters.

OUTPUT FORMAT (JSON only, no other text):
{{"title": "English song title (max 50 chars)", "style": "Genre", "prompt": "Music description (max 150 chars)"}}

RULES:
1. title: Creative English song title based on the Korean input
2. style: One genre from: K-Pop, Pop, Rock, Ballad, Jazz, Electronic, Folk, R&B, Hip-Hop, Classical
3. prompt: Concise music description with mood, tempo, instruments. Include "Korean female vocals" for vocal tracks.
4. Output ONLY valid JSON, nothing else

Example input: 여름의 장미
Example output: {{"title": "Summer Rose", "style": "K-Pop", "prompt": "Romantic dreamy K-Pop, 80 BPM, piano strings guitar, soft Korean female vocals"}}"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt_text),
            ("human", "{input}"),
        ])
        
        try:
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({"input": korean_input})
            response = response.strip()
            
            print(f"[Llama] 원본 응답: {response}")
            
            # JSON 파싱 시도
            try:
                # JSON 부분만 추출 (앞뒤 텍스트 제거)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    print(f"[Llama] 파싱된 결과: {result}")
                    return result
            except json.JSONDecodeError:
                pass
            
            # JSON 파싱 실패 시 기본값으로 폴백
            print(f"[Llama] JSON 파싱 실패, 기본값 사용")
            return {
                'title': korean_input[:50],
                'style': 'K-Pop',
                'prompt': f"Korean pop song about {korean_input}, melodic, 90 BPM, piano guitar, Korean female vocals"
            }
            
        except Exception as e:
            print(f"[Llama] 프롬프트 변환 오류: {e}")
            return None
    
    def convert_to_music_prompt(self, korean_input: str) -> Optional[str]:
        """
        기존 호환성을 위한 메서드 (deprecated)
        """
        result = self.generate_music_params(korean_input)
        if result:
            return result.get('prompt')
        return None


class SunoAPIService:
    """
    Suno API를 호출하여 음악을 생성하는 서비스
    Polling 방식으로 음악 생성 완료까지 대기
    """
    
    def __init__(self):
        self.api_key = os.getenv('SUNO_API_KEY')
        self.api_url = os.getenv('SUNO_API_URL', 'https://api.sunoapi.org')
        # 모델 버전: V4_5, V4_5ALL, V4_5PLUS, V5 등
        model_env = os.getenv('SUNO_MODEL_VERSION', 'V4_5')
        # 환경 변수에 점(.)이 있으면 언더스코어로 변환 (V4.5 -> V4_5)
        self.model_version = model_env.replace('.', '_')
        
        # 테스트 모드: SUNO_TEST_MODE=true로 설정하면 실제 API 호출 없이 Mock 데이터 반환
        self.test_mode = os.getenv('SUNO_TEST_MODE', 'false').lower() in ('true', '1', 'yes')
        
        if not self.api_key and not self.test_mode:
            raise ValueError("SUNO_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        if self.test_mode:
            print(f"[Suno API] ⚠️ 테스트 모드 활성화 - 실제 API 호출 없이 Mock 데이터 반환")
        else:
            print(f"[Suno API] 초기화 - Base URL: {self.api_url}")
            print(f"[Suno API] API Key: {self.api_key[:10]}...")
        print(f"[Suno API] Model Version: {self.model_version}")
    
    def _get_headers(self) -> Dict[str, str]:
        """API 요청 헤더 생성"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def _get_callback_url(self) -> str:
        """
        콜백 URL 가져오기 및 검증
        
        Returns:
            검증된 콜백 URL
        """
        callback_url = os.getenv('SUNO_CALLBACK_URL', '').strip()
        
        # 환경 변수가 없거나 비어있으면 기본값 사용
        if not callback_url:
            callback_url = 'https://webhook.site/unique-uuid'
            print(f"[Suno API] ⚠️ SUNO_CALLBACK_URL이 설정되지 않아 기본값 사용: {callback_url}")
            return callback_url
        
        # URL 형식 검증
        if not callback_url.startswith(('http://', 'https://')):
            print(f"[Suno API] ⚠️ 잘못된 콜백 URL 형식: {callback_url}")
            print(f"[Suno API] ⚠️ 기본값 사용: https://webhook.site/unique-uuid")
            return 'https://webhook.site/unique-uuid'
        
        print(f"[Suno API] 콜백 URL: {callback_url}")
        
        # ngrok 사용 시 경고
        if 'ngrok' in callback_url:
            print(f"[Suno API] ✅ ngrok 사용 중: {callback_url}")
        
        return callback_url
    
    def _validate_callback_url(self, url: str) -> bool:
        """
        콜백 URL 유효성 검증
        """
        try:
            if not url.startswith(('http://', 'https://')):
                return False
            
            # localhost는 외부에서 접근 불가
            if 'localhost' in url or '127.0.0.1' in url:
                print(f"[Suno API] ⚠️ localhost URL은 외부에서 접근할 수 없습니다: {url}")
                return False
            
            return True
        except Exception as e:
            print(f"[Suno API] 콜백 URL 검증 오류: {e}")
            return False
    
    def generate_music(
        self, 
        prompt: str, 
        style: str = None,
        title: str = None,
        make_instrumental: bool = False,
        wait_audio: bool = True,
        timeout: int = 180
    ) -> Optional[Dict]:
        """
        Suno API를 사용하여 음악 생성 (Polling 방식)
        
        Args:
            prompt: 음악 생성 프롬프트 (영어)
            style: 음악 장르/스타일
            title: 음악 제목
            make_instrumental: 반주만 생성할지 여부
            wait_audio: 음악 생성 완료까지 대기할지 여부
            timeout: 최대 대기 시간 (초)
            
        Returns:
            완성된 음악 데이터 딕셔너리 또는 {'taskId': '...', 'status': 'pending'}
        """
        try:
            # Step 1: 음악 생성 요청
            request_result = self._request_music_generation(
                prompt=prompt,
                style=style,
                title=title,
                make_instrumental=make_instrumental
            )
            
            if not request_result:
                print("[Suno API] 생성 요청 실패")
                return None
            
            # 생성 요청 응답에 바로 audioUrl이 있는지 확인
            if request_result.get('audioUrl') or request_result.get('audio_url'):
                print(f"[Suno API] ✅ 생성 요청 응답에 바로 audioUrl 발견!")
                return request_result
            
            if not request_result.get('taskId'):
                print("[Suno API] taskId를 받지 못했습니다.")
                return None
            
            task_id = request_result['taskId']
            status_url = request_result.get('statusUrl')
            check_url = request_result.get('checkUrl')
            
            print(f"[Suno API] 음악 생성 시작 - taskId: {task_id}")
            
            # Step 2: Polling으로 완료 대기
            if wait_audio:
                music_data = self._poll_task_status(
                    task_id, timeout, 
                    prompt=prompt, style=style, title=title,
                    status_url=status_url, check_url=check_url
                )
                
                if music_data:
                    print(f"[Suno API] 음악 생성 완료!")
                    if 'taskId' not in music_data:
                        music_data['taskId'] = task_id
                    return music_data
                else:
                    print(f"[Suno API] Polling 실패 또는 타임아웃, 기본 데이터 반환")
                    return {
                        'taskId': task_id,
                        'status': 'pending',
                        'title': title or 'AI Generated Song',
                        'prompt': prompt,
                        'style': style,
                        'audioUrl': None,
                        'duration': None,
                        'lyrics': None,
                        'imageUrl': None,
                        'genre': style 
                    }
            else:
                return {'taskId': task_id}
            
        except Exception as e:
            print(f"[Suno API] 음악 생성 중 오류: {e}")
            return None
    
    def _get_mock_music_data(self, prompt: str, style: str, title: str) -> Dict:
        """
        테스트 모드용 Mock 음악 데이터 생성
        """
        import uuid
        task_id = str(uuid.uuid4()).replace('-', '')[:32]
        
        return {
            'taskId': task_id,
            'audioUrl': f'https://cdn.suno.ai/mock/{task_id}.mp3',
            'title': title or 'Mock Test Song',
            'duration': 180,
            'lyrics': f'[Mock 가사]\n{prompt}\n\n이것은 테스트용 Mock 데이터입니다.',
            'imageUrl': f'https://cdn.suno.ai/mock/{task_id}.jpg',
            'genre': style or 'Pop',
            'valence': 0.75,
            'arousal': 0.65,
            'status': 'completed'
        }
    
    def _request_music_generation(
        self, 
        prompt: str, 
        style: str = None,
        title: str = None,
        make_instrumental: bool = False
    ) -> Optional[Dict]:
        """
        Suno API에 음악 생성 요청하고 taskId 반환
        """
        # 테스트 모드면 Mock taskId 반환
        if self.test_mode:
            import uuid
            task_id = str(uuid.uuid4()).replace('-', '')[:32]
            print(f"[Suno API] 테스트 모드: Mock taskId 생성 - {task_id}")
            return {'taskId': task_id, 'statusUrl': None, 'checkUrl': None}
        
        try:
            callback_url = self._get_callback_url()
            
            if not self._validate_callback_url(callback_url):
                callback_url = 'https://webhook.site/unique-uuid'
            
            data = {
                'customMode': True,
                'instrumental': make_instrumental,
                'model': self.model_version,
                'callBackUrl': callback_url,
                'prompt': prompt, 
                'style': style,
                'title': title or 'AI Generated Song',
                'wait_audio': True,
                'personaId': '',
                'negativeTags': '',
                'vocalGender': '',
                'styleWeight': 0.5,
                'weirdnessConstraint': 0.5,
                'audioWeight': 0.5
            }
            
            print(f"[Suno API] 생성 요청 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            endpoint = f'{self.api_url}/api/v1/generate'
            
            print(f"[Suno API] 요청 URL: {endpoint}")
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=data,
                timeout=60
            )
            
            print(f"[Suno API] 응답 상태: {response.status_code}")
            result = response.json()
            print(f"[Suno API] 응답: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 크레딧 부족 오류 체크
            if result.get('code') == 429:
                error_msg = result.get('msg', '크레딧이 부족합니다.')
                raise SunoCreditInsufficientError(f"Suno API 크레딧 부족: {error_msg}")
            
            # 인증 오류 체크
            if result.get('code') == 401:
                error_msg = result.get('msg', 'API 키 인증 실패')
                raise SunoAuthenticationError(f"Suno API 인증 실패: {error_msg}")
            
            if response.status_code == 200 and result.get('code') == 200 and result.get('data'):
                data = result['data']
                task_id = data.get('taskId')
                
                audio_url = (
                    data.get('audioUrl') or 
                    data.get('audio_url') or 
                    data.get('url') or
                    (isinstance(data.get('audio_urls'), list) and len(data.get('audio_urls', [])) > 0 and data['audio_urls'][0])
                )
                
                if task_id:
                    print(f"[Suno API] 생성 요청 성공 - taskId: {task_id}")
                    
                    if audio_url:
                        print(f"[Suno API] ✅ 생성 요청 응답에 바로 audioUrl 발견: {audio_url}")
                        return {
                            'taskId': task_id,
                            'audioUrl': audio_url,
                            'title': data.get('title') or title or 'AI Generated Song',
                            'duration': data.get('duration') or data.get('length'),
                            'lyrics': data.get('lyrics') or data.get('lyric'),
                            'imageUrl': data.get('imageUrl') or data.get('image_url'),
                            'genre': data.get('genre') or data.get('style') or style or 'Pop',
                            'status': 'completed',
                            'statusUrl': data.get('statusUrl'),
                            'checkUrl': data.get('checkUrl')
                        }
                    
                    return {
                        'taskId': task_id,
                        'statusUrl': data.get('statusUrl'),
                        'checkUrl': data.get('checkUrl')
                    }
            
            error_msg = result.get('msg', '알 수 없는 오류')
            raise Exception(f"Suno API 오류 (code: {result.get('code')}): {error_msg}")
            
        except Exception as e:
            print(f"[Suno API] 생성 요청 오류: {e}")
            return None
    
    def _poll_task_status(
        self, 
        task_id: str, 
        timeout: int = 300, 
        prompt: str = None, 
        style: str = None, 
        title: str = None, 
        status_url: str = None, 
        check_url: str = None
    ) -> Optional[Dict]:
        """
        taskId로 작업 상태를 Polling하여 완료될 때까지 대기
        """
        # 테스트 모드면 즉시 Mock 데이터 반환
        if self.test_mode:
            print(f"[Suno API] 테스트 모드: Polling 스킵, Mock 데이터 반환")
            time.sleep(2)
            return self._get_mock_music_data(prompt or 'Test prompt', style or 'Pop', title or 'Test Song')
        
        poll_interval = 3
        max_attempts = timeout // poll_interval
        
        # 상태 조회 엔드포인트
        status_endpoints = []
        
        if status_url:
            status_endpoints.append(status_url)
        if check_url:
            status_endpoints.append(check_url)
        
        # POST 방식
        status_endpoints.extend([
            (f'{self.api_url}/api/v1/music/{task_id}', {}),
            (f'{self.api_url}/api/v1/get', {'taskId': task_id}),
            (f'{self.api_url}/api/v1/task', {'taskId': task_id}),
            (f'{self.api_url}/api/v1/query', {'taskId': task_id}),
        ])
        
        # GET 방식
        status_endpoints.extend([
            f'{self.api_url}/api/v1/music/{task_id}',
            f'{self.api_url}/api/v1/get/{task_id}',
            f'{self.api_url}/api/v1/task/{task_id}',
        ])
        
        consecutive_404_count = 0
        max_consecutive_404 = len(status_endpoints)
        
        print(f"[Suno API] Polling 시작 - taskId: {task_id}, 최대 대기: {timeout}초")
        
        for attempt in range(max_attempts):
            if attempt > 0:
                time.sleep(poll_interval)
            
            print(f"[Suno API] Polling 시도 {attempt+1}/{max_attempts}...")
            
            for endpoint_item in status_endpoints:
                try:
                    if isinstance(endpoint_item, tuple):
                        endpoint_url, post_data = endpoint_item
                        method = "POST"
                        response = requests.post(
                            endpoint_url,
                            headers=self._get_headers(),
                            json=post_data,
                            timeout=30
                        )
                    else:
                        endpoint_url = endpoint_item
                        method = "GET"
                        response = requests.get(
                            endpoint_url,
                            headers=self._get_headers(),
                            timeout=30
                        )
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            consecutive_404_count = 0
                            
                            if result.get('code') == 200 and result.get('data'):
                                data = result['data']
                                
                                audio_url = (
                                    data.get('audioUrl') or 
                                    data.get('audio_url') or 
                                    data.get('url')
                                )
                                
                                if audio_url:
                                    print(f"[Suno API] ✅ 음악 데이터 발견!")
                                    if 'audioUrl' not in data and audio_url:
                                        data['audioUrl'] = audio_url
                                    return data
                                
                                status = str(data.get('status', '')).lower()
                                
                                if status in ['completed', 'complete', 'success', 'done']:
                                    print(f"[Suno API] ✅ 음악 생성 완료!")
                                    return data
                                elif status in ['failed', 'error', 'failure']:
                                    print(f"[Suno API] ❌ 음악 생성 실패")
                                    return None
                                elif status in ['pending', 'processing', 'generating', 'queued', 'running', '']:
                                    print(f"[Suno API] ⏳ 진행 중...")
                                    break
                                    
                        except json.JSONDecodeError as e:
                            print(f"[Suno API] JSON 파싱 오류: {e}")
                            continue
                        
                        break
                        
                    elif response.status_code == 404:
                        consecutive_404_count += 1
                        
                        if consecutive_404_count >= max_consecutive_404:
                            print(f"[Suno API] ⚠️ 모든 엔드포인트가 404 - Polling 조기 종료")
                            return {
                                'taskId': task_id,
                                'status': 'pending',
                                'title': title or 'AI Generated Song',
                                'prompt': prompt,
                                'style': style or 'Pop',
                                'audioUrl': None,
                                'duration': None,
                                'lyrics': None,
                                'imageUrl': None,
                                'genre': style or 'Pop'
                            }
                        continue
                    else:
                        continue
                        
                except requests.exceptions.Timeout:
                    continue
                except requests.exceptions.RequestException as e:
                    continue
                except Exception as e:
                    continue
        
        print(f"[Suno API] ❌ Polling 타임아웃")
        return {
            'taskId': task_id,
            'status': 'pending',
            'title': title or 'AI Generated Song',
            'prompt': prompt,
            'style': style,
            'audioUrl': None,
            'duration': None,
            'lyrics': None,
            'imageUrl': None,
            'genre': style or 'Pop'
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        단일 상태 조회 (외부에서 호출용)
        """
        status_endpoints = [
            (f'{self.api_url}/api/v1/get', {'taskId': task_id}),
            (f'{self.api_url}/api/v1/task', {'taskId': task_id}),
            f'{self.api_url}/api/v1/task/{task_id}',
            f'{self.api_url}/api/v1/get/{task_id}',
        ]
        
        for endpoint_item in status_endpoints:
            try:
                if isinstance(endpoint_item, tuple):
                    endpoint_url, post_data = endpoint_item
                    response = requests.post(
                        endpoint_url,
                        headers=self._get_headers(),
                        json=post_data,
                        timeout=30
                    )
                else:
                    endpoint_url = endpoint_item
                    response = requests.get(
                        endpoint_url,
                        headers=self._get_headers(),
                        timeout=30
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('code') == 200 and result.get('data'):
                        return result['data']
                    elif isinstance(result, dict) and (result.get('audioUrl') or result.get('audio_url')):
                        return result
                        
            except Exception as e:
                continue
        
        return None
    
    def get_music_info(self, music_id: str) -> Optional[Dict]:
        """
        생성된 음악 정보 조회
        """
        try:
            response = requests.get(
                f'{self.api_url}/api/music/{music_id}',
                headers=self._get_headers(),
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"음악 정보 조회 실패: {e}")
            return None
    
    def get_timestamped_lyrics(self, record_id: str) -> Optional[str]:
        """
        타임스탬프 가사 조회 및 포맷팅
        """
        if self.test_mode:
            print(f"[Suno API] 테스트 모드: 타임스탬프 가사 Mock 데이터 반환")
            return "[0.0] [Verse]\n[1.0] Test lyrics"
        
        try:
            endpoint1 = f'{self.api_url}/api/v1/lyrics/record-info/{record_id}'
            endpoint2 = f'{self.api_url}/api/v1/lyrics/record-info'
            
            params_list = [
                {'taskId': record_id},
                {'task_id': record_id},
                {'record_id': record_id},
                {'id': record_id},
            ]
            
            try:
                response = requests.get(
                    endpoint1,
                    headers=self._get_headers(),
                    timeout=30
                )
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
            except:
                response = None
                for params in params_list:
                    try:
                        response = requests.get(
                            endpoint2,
                            headers=self._get_headers(),
                            params=params,
                            timeout=30
                        )
                        if response.status_code == 200:
                            break
                    except:
                        continue
                
                if not response:
                    raise Exception("모든 방법 실패")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 200:
                    data = result.get('data')
                    if not data:
                        return None
                    
                    aligned_words = data.get('alignedWords', []) if isinstance(data, dict) else []
                    
                    if not aligned_words:
                        return None
                    
                    # 타임스탬프 가사 포맷팅
                    timestamped_lyrics = []
                    for word_data in aligned_words:
                        word = word_data.get('word', '').strip()
                        start_s = word_data.get('startS', 0)
                        end_s = word_data.get('endS', 0)
                        
                        if word:
                            if start_s and end_s:
                                timestamped_lyrics.append(f"{word} [{start_s:.2f}-{end_s:.2f}]")
                            elif start_s:
                                timestamped_lyrics.append(f"{word} [{start_s:.2f}]")
                            else:
                                timestamped_lyrics.append(word)
                    
                    return '\n'.join(timestamped_lyrics)
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"[Suno API] 타임스탬프 가사 조회 오류: {e}")
            return None
