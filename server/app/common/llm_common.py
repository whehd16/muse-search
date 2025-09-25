import requests
import copy
import logging
import json

class MuseLLM:
    _gemma_url = "http://ai-int.mbc.co.kr:8000/v1/chat/completions" 
    _oss_url = "http://ai-int.mbc.co.kr:9000/v1/chat/completions"
    
    _system_prompt = """
     음악 검색 쿼리를 분석하여 JSON 형식으로 반환해주세요.

        ## JSON 스키마
        {
        "artist": [],     // 아티스트명 (한글/영어 병기)
        "title": [],      // 곡명 또는 제목 키워드
        "region": [],     // 지역 구분 배열 (region과 genre가 인덱스별로 1:1 매핑)
        "genre": [],      // 장르 배열 (region과 genre가 인덱스별로 1:1 매핑)
        "mood": [],       // 분위기/감정
        "popular": [],    // 인기도 [true/false] (default: [false])
        "year": [],       // 연도 범위 [시작, 끝]
        "vibe": [],       // CLAP 임베딩용 영어 설명 (추천 쿼리에만)
        "lyrics": [],     // 가사 검색어
        "lyrics_summary": [], // 가사 요약 임베딩용 영어 설명 (가사 관련 쿼리에만)
        "case": 0         // 케이스 번호 (0-12)
        }

        ## 파싱 규칙

        ### 기본 원칙
        1. **쿼리에 명시된 정보만 추출** (추측 금지)
        2. **아티스트명, 노래제목은 한글/영어 병기** (가능한 경우)
        3. **가사 검색어는 lyrics 필드에만 입력**
        4. **사용자 쿼리에 mood 값이 포함되어 있다면 반환 mood 리스트에도 포함할것(영어가 아니면 영어로 번역해서 대체할 것)
        5. **vibe는 추천성 쿼리에만 생성** (CLAP 임베딩용 영어 설명, 음악적 특징/분위기만 포함, 아티스트 및 제목 정보 절대 넣지 말 것)
        6. **lyrics_summary는 가사 관련 쿼리에 생성** (가사 내용/주제를 영어로 요약, vibe와 동일 형식)
        7. **popular는 명시적 언급시에만 [true]. 기본값은 [false]** ("유명한", "히트곡" 등)
        8. **region과 genre 필드 매핑**:
           • region과 genre 배열의 같은 인덱스끼리 1:1 매핑됨
           • 예: "국내 재즈와 해외 팝" → region: ["국내", "외국"], genre: ["재즈", "팝"]
           • 예: "2020년대 국내 일렉과 해외 댄스 그리고 해외 팝" → region: ["국내", "외국", "외국"], genre: ["일렉", "댄스", "팝"]
           • region이 명시되지 않은 장르는 "전체"로 설정
           • 예: "재즈와 클래식" → region: ["전체", "전체"], genre: ["재즈", "클래식"]
           • genre가 명시되지 않은 region은 빈 문자열 ""로 설정
           • 예: "재즈와 클래식" → region: ["국내"], genre: [""]
        9. **genre 필드는 다음 중에서만 선택**: ["재즈", "힙합", "댄스", "락", "팝", "포크", "일렉", "R&B", "컨추리", "블루스", "메탈", "트로트", "크로스오버", "클래식", "어린이", "OST", "뉴에이지", "국악", "종교", "캐롤", "효과음"]           
           • region과 동일한 길이의 배열로 반환         
        10. **"최신", "요즘", "최근" 등의 키워드 처리**:
           • "최신 유행곡", "요즘 유행하는", "최근 인기곡" → year: [2024, 2025], popular: [true]
           • "최신곡", "최근 발매곡" → year: [2024, 2025]
           • 현재 연도는 2025년 기준으로 자동 설정
           • "올해" → year: [2025, 2025]
           • "작년" → year: [2024, 2024]
           • "최근 몇 년" → year: [2022, 2025]
        
        ### 오탈자 처리 원칙
        - **아티스트명과 곡명에서 오탈자 처리**:
          • 원본 텍스트를 먼저 포함
          • 명백한 오탈자가 있다면 수정된 버전도 추가
          • 예: "biutyful" → ["biutyful", "beautiful"] (원본 먼저, 수정 버전 추가)          
        - **실제 존재하는 곡명/아티스트명 우선 보존**
          • 오탈자처럼 보여도 실제 존재할 수 있는 이름은 원본 유지
          • 예: "biutyful"이라는 실제 곡이 있을 수 있음
        
        ### title 필드 사용 기준
        - **우선 사용하는 경우**: 
          • 사용자가 명시적으로 "제목에 ~가 들어간" 요청 (예: "제목에 사랑이 들어간 노래")
          • 날씨/계절의 직접적 언급 (예: "비", "크리스마스" - 높은 확률로 제목에 포함)
        
        - **선택적 사용 (상황에 따라 판단)**:
          • 상황/활동 설명: 일부만 title에 포함, 주로 mood/vibe 활용
            - "운동할 때" → title 미사용, vibe: ["energetic workout music"]
            - "노래방에서" → title에 일부 인기곡 키워드 가능, 주로 mood 활용
            - "엄마랑 같이" → title 미사용, vibe: ["family friendly warm music"]
        
        - **사용하지 않는 경우**:
          • 악기/음향 특징 (예: "피아노와 일렉기타가 인상적인" → vibe로만 처리)
          • 순수한 분위기/감정 (예: "편안한 분위기")
          • 음악적 특징 설명 (예: "템포가 빠른", "어쿠스틱한")

        ### 케이스 분류

        | Case | 설명 | 예시 쿼리 | 주요 필드 |
        |------|------|-----------|-----------|
        | 0 | 특정 가수 검색 | "이승철 노래" | artist |
        | 1 | 제목 키워드 검색 | "제목에 사랑이 들어간 노래" | title |
        | 2 | 가수+곡명 검색 | "아이유 좋은날" | artist, title |
        | 3 | 조건 검색 | "90년대 유행한 힙합" | region, genre, year, popular |
        | 4 | 가수+조건 검색 | "빌리 아일리시 2020년 히트곡" | artist, year, popular |
        | 5 | 가수+느낌 검색 | "뉴진스 같은 Y2K 노래" | artist, mood, vibe(Y2K 특징만) |
        | 6 | 감정/상황 추천(구체적) | "운동할 때 듣기 좋은 노래" | mood, vibe(상황 분위기) |
        | 7 | 감정/상황 추천(추상적) | "자연 소리와 앰비언트 패드가 조화를 이룬 힐링용 연주곡" | mood, vibe(상세 설명)|
        | 8 | 가수 + 감정/상황 추천 | "빌리 아일리시 노래 중에 슬플 때 기운나는 노래 추천해줘" | artist, mood, vibe(분위기만) |
        | 9 | 가사 검색 | "니가 없는 거리에는 가사 들어간 노래" | lyrics(니가 없는 거리에는), lyrics_summary(songs about empty streets without you) |
        | 10 | 상황별 센스있는 추천 | "배고플 때 듣는 노래" | title, mood, vibe(재치있는 분위기) |
        | 11 | 줄글에 대한 상황 요약 후 추천 | 라디오 사연, 기사 등과 같은 줄글 | title, mood, vibe |
        | 12 | 나머지 분류가 안될 때(예외 케이스) | |

        ### 특별 처리 사항
        - ** 유사단어 체크 ** "노래"="음악"="곡"
        - **Case 6 vs Case 7 구분**: 
          • Case 6: 구체적 상황 → 선택적 title 사용, 주로 mood/vibe 활용
          • Case 7: 추상적/감성적 표현 → title 미사용, vibe에 상세 설명
        - **Case 10**: 재치있는 상황은 선택적 title, 주로 mood/vibe 활용
        - **vibe 생성**: 음악적 특징/분위기만 영어로 표현 (아티스트명 제외, CLAP 모델 최적화)
        - **lyrics_summary 생성**: 가사 검색 쿼리를 영어로 의미있게 요약 (vibe와 동일한 형식)
        - **애매한 텍스트**: 노래 제목인지 불확실한 경우 title에서 제외
        
        ### 예시 분석
        1. "비오는날 듣기 좋은 노래" → title: ["비", "rain"], vibe: ["relaxing music for rainy days"]
        2. "자연 소리와 앰비언트 패드가 조화를 이룬 힐링용 연주곡" → title: [], vibe: ["healing instrumental with nature sounds and ambient pads"]
        3. "크리스마스 분위기 노래" → title: ["크리스마스", "christmas"], vibe: ["festive christmas mood"]
        4. "편안하고 차분한 음악" → title: [], vibe: ["calm relaxing peaceful"]
        5. "이별 후 혼자 남은 가사가 있는 노래" → lyrics: ["이별 후 혼자"], lyrics_summary: ["being alone after breakup"]
        6. "사랑한다고 말하는 가사" → lyrics: ["사랑한다"], lyrics_summary: ["expressing love and confession"]
        7. "칸예웨스트 노래 중에 피아노 선율로 시작하는 노래" → artist: ["Kanye West", "칸예웨스트"], vibe: ["piano melody beginning"], case: 5
        8. "BTS 노래 중 신나는 댄스곡" → artist: ["BTS", "방탄소년단"], vibe: ["upbeat dance energetic"], case: 8
        9. "엄마랑 같이 듣기 좋은 노래" → title: [], mood: ["warm", "family"], vibe: ["family friendly warm music"], case: 6
        10. "친구들이랑 노래방에서 부를 노래" → title: [], mood: ["fun", "party"], vibe: ["karaoke party singalong"], popular: [true], case: 6
        11. "데이트할 때 틀면 좋은 노래" → title: [], mood: ["romantic", "sweet"], vibe: ["romantic date atmosphere"], case: 6
        12. "운동할 때 듣기 좋은 노래" → title: [], mood: ["energetic", "powerful"], vibe: ["energetic workout motivation"], case: 6
        13. "피아노와 일렉기타가 인상적인 노래" → title: [], vibe: ["impressive piano and electric guitar"], case: 7

        JSON 형식으로만 응답하세요.
    """

    _gemma_payload = {
        "model": "google/gemma-3-27b-it",
        "messages": [
            {
                "role": "system",
                "content": _system_prompt
            },

            {
                "role": "user",
                "content": "쿼리"
            }
        ],            
        "max_tokens": 500,
        "temperature": 0.5,
        "response_format": {"type": "json_object"}  # JSON 응답 강제 (지원되면)
    }

    _oss_payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": _system_prompt
            },

            {
                "role": "user",
                "content": "쿼리"
            }
        ],            
        "max_tokens": 500,
        "temperature": 0.5,
        "response_format": {"type": "json_object"}  # JSON 응답 강제 (지원되면)
    }

    @staticmethod
    def make_system_reason_prompt(text, llm_result, song_info):

        return f"""
        아래는 사용자의 음악 검색 요청에 대한 결과입니다. 
        자연스럽고 친근한 응답으로 음악을 추천해주세요.

        사용자 요청: {text}

        사용자 요청에 대한 FAISS 처리 목록: {llm_result}

        최종 추천곡:
        {song_info}

        요청사항:
        1. 각 곡에 대해 왜 추천하는지 간단한 설명 추가  
        2. 자연스러운 대화체로 응답
        3. 반환 형태: dict(key: 'description', value: ['추천 이유'])
        4. 한국어로 된 추천 이유만 반환할 것        
        
        JSON 형식으로만 응답하세요.
    """

    @staticmethod
    # "model": "google/gemma-3-27b-it",
    def make_system_reason_payload(prompt):
        return {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": prompt
            },

            {
                "role": "user",
                "content": "쿼리"
            }
        ],            
        "max_tokens": 1000,
        "temperature": 0.4,
        "response_format": {"type": "json_object"}  # JSON 응답 강제 (지원되면)
    }

    @staticmethod
    def get_request(text, mood, llm_type='gemma'):
        try:            
            if llm_type == 'gemma':
                MuseLLM._gemma_payload['messages'][1]['content'] = f'''쿼리: {text}, 무드: {mood}'''
                response = requests.post(MuseLLM._gemma_url, json= MuseLLM._gemma_payload)
            elif llm_type == 'oss':
                MuseLLM._oss_payload['messages'][1]['content'] = f'''쿼리: {text}, 무드: {mood}'''
                response = requests.post(MuseLLM._oss_url, json= MuseLLM._oss_payload)        
            
            # 응답 파싱
            if response.status_code == 200:
                data = response.json()      
                results = json.loads(data['choices'][0]['message']['content'])
                results['llm_model'] = llm_type                            
                return results
            else:
                logging.error(f'''오류: {response.status_code}, {response.text}''')
                return None
        except Exception as e:
            logging.error(e)
            return None

    @staticmethod
    def get_reason(text, llm_result, song_info):
        response = requests.post(MuseLLM._oss_url, json= MuseLLM.make_system_reason_payload(prompt=MuseLLM.make_system_reason_prompt(text=text, llm_result=llm_result, song_info=song_info)))
        # 응답 파싱
        if response.status_code == 200:
            data = response.json()            
            return data['choices'][0]['message']['content']            
        else:
            logging.error("오류:", response.status_code, response.text)
            return None