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
        "artist": [],     // 아티스트명 (한글/영어 병기, 소문자로만)
        "title": [],      // 곡명 또는 제목 키워드
        "album_name": [], // 앨범명 (한글/영어 병기) (default: [])
        "region": [],     // 지역 구분 배열 (region과 genre가 인덱스별로 1:1 매핑)
        "genre": [],      // 장르 배열 (region과 genre가 인덱스별로 1:1 매핑)
        "mood": [],       // 분위기/감정
        "popular": [],    // 인기도 [true/false] (default: [false])
        "year": [],       // 연도 범위 [시작, 끝]
        "vibe": [],       // CLAP 임베딩용 영어 설명 (추천 쿼리에만)
        "lyrics": [],     // 가사 검색어
        "lyrics_summary": [], // 가사 요약 임베딩용 영어 설명 (가사 관련 쿼리에만)
        "case": 0         // 케이스 번호 (0-14)
        }

        ## 파싱 규칙

        ### 핵심 규칙

        ⚠️ **[최우선] region과 genre는 항상 같은 길이의 배열이어야 함**
           • 두 배열의 같은 인덱스가 서로 매핑됨
           • "국내 재즈와 해외 팝" → region: ["국내", "외국"], genre: ["재즈", "팝"]
           • "재즈와 클래식" → region: ["전체", "전체"], genre: ["재즈", "클래식"]
           • "국내 음악" → region: ["국내"], genre: [""]
           • genre만 있으면 region은 "전체"로, region만 있으면 genre는 ""로 채움

        1. **쿼리에 명시된 정보만 추출** (추측 금지)
        2. **한글/영어 병기**: artist, title, album_name
        3. **album_name**:
           • OST, 디즈니, 픽사, 지브리, 등 앨범 시리즈는 artist와 album_name 모두에 포함
           • "앨범", "정규", "미니", "영화", "드라마" 키워드가 명시적으로 있으면 album_name에만 포함 
           • 키워드가 없을 때: 사용자가 어느 필드인지 명확하지 않으면 관련 필드에 모두 포함
           • 예: "케이팝데몬헌터스 골든" → album_name: ["케이팝데몬헌터스"], artist: ["케이팝데몬헌터스"], title: ["골든"]
           • 예: "디즈니 인어공주" → artist: ["디즈니", "Disney"], album_name: ["디즈니", "Disney", "인어공주", "The Little Mermaid"]
           • 기본값 []
        4. **popular**: "유명한", "히트곡" 언급시 [true]. 기본값 [false]
        5. **genre 선택지**: ["재즈", "힙합", "댄스", "락", "팝", "포크", "일렉", "R&B", "컨추리", "블루스", "메탈", "트로트", "크로스오버", "클래식", "어린이", "OST", "뉴에이지", "국악", "종교", "캐롤", "효과음"]
        6. **시간 키워드**: "최신/요즘/올해"→[2025], "작년"→[2024], "최근 몇년"→[2022,2025]
        
        ### 추가 규칙

        - **오탈자**: 원본 먼저, 수정 버전 추가. 예: ["biutyful", "beautiful"]
        - **title 사용**: "제목에 ~가 들어간" 명시적 요청이나 날씨/계절만. 나머지는 mood/vibe 활용
        - **vibe**: 추천 쿼리의 음악적 특징/분위기를 영어로 (CLAP 임베딩용 영어 설명, 음악적 특징/분위기만 포함, 아티스트 및 제목 정보 절대 넣지 말 것)
        - **lyrics_summary**: 가사 쿼리를 영어로 요약

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
        | 9 | 가사 검색 | "니가 없는 거리에는 라는 가사 들어간 노래" | lyrics(니가 없는 거리에는) |
        | 10 | 앨범 검색 | "버터플라이 앨범", "아이유 Modern Times 앨범", "영화 어벤져스의 노래" | album_name (+ artist 선택적) |
        | 11 | 앨범+조건 검색 | "Love Yourself 앨범에서 슬픈 노래" | album_name, mood/genre/vibe |
        | 12 | 상황별 센스있는 추천 | "배고플 때 듣는 노래" | title, mood, vibe(재치있는 분위기), lyrics_summary |
        | 13 | 줄글에 대한 상황 요약 후 추천 | 라디오 사연, 기사 등과 같은 줄글 | title, mood, vibe, lyrics_summary |
        | 14 | 나머지 분류가 안될 때(예외 케이스) | |

        ### 핵심 예시
        1. "비오는날 듣기 좋은 노래" → title: ["비", "rain"], vibe: ["relaxing music for rainy days"]
        2. "국내 재즈와 해외 팝" → region: ["국내", "외국"], genre: ["재즈", "팝"]
        3. "재즈와 클래식" → region: ["전체", "전체"], genre: ["재즈", "클래식"]
        4. "국내 음악" → region: ["국내"], genre: [""]
        5. "아이유 Modern Times 앨범" → artist: ["아이유", "IU"], album_name: ["Modern Times", "모던 타임즈"]
        6. "'이별 후 혼자' 라는 가사 들어간 노래" → lyrics: ["이별 후 혼자"]
        7. "케이팝데몬헌터스 골든" → artist: ["케이팝데몬헌터스", "K-POP Demon Hunters"], album_name: ["케이팝데몬헌터스", "K-POP Demon Hunters"], title: ["골든", "Golden"]
        8. "디즈니 OST" → artist: ["디즈니", "Disney"], album_name: ["디즈니", "Disney"], genre: ["OST"]
        9. "디즈니 인어공주 노래" → artist: ["디즈니", "Disney"], album_name: ["디즈니", "Disney", "인어공주", "The Little Mermaid"]

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

        return f"""Generate ONE concise recommendation reason for the music search result.

            User query: {text}
            Search results: {llm_result}
            Final songs: {song_info}

            Return format:
            {{"description": ["one specific reason in Korean"]}}

            Guidelines:
            - Write ONE clear reason why this song matches the user's request
            - Use friendly, natural Korean
            - Be specific about the song's characteristics (mood, artist style, genre, etc.)
            - Keep it concise (1-2 sentences)

            Example:
            {{"description": ["어떤어떤 이유로 추천합니다."]}}

            Return ONLY the JSON object:"""

    @staticmethod
    def make_system_reason_payload(prompt):
        return {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "system",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.3
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