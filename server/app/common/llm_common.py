import requests
import copy

class MuseLLM:
    _gemma_url = "http://ai-int.mbc.co.kr:8000/v1/chat/completions"
    # "genre: pop, mood: energetic, instruments: guitar drums, tempo: fast"

    # 예시)
    #     장르 키워드 + 감정 키워드 + 악기/사운드 키워드 조합
    #     "pop music in energentic vibe with fast guitar and drums tempo


    # 사용자의 음악 검색을 위한 텍스트를 줄게. 1단계, 2단계에 맞게 작업을 해서 문자열 하나만 반환해. 
    #     1단계: 주어진 입력 텍스트를 영어로 번역해.
    #     2단계: 1단계에서 영어로 번역된 문장을 CLAP(Contrastive Language-Audio Pre-training)의 텍스트 임베딩을 위해서 문장 내용을 분석해서 음악적 특성을 추출해줘.
    #     3단계:
    #     ex)
    #         “melancholic classical piano piece”
    #         “ambient electronic music for studying”
    #         “jazzy hip hop beat with soft drums and vinyl crackle”
    #     아래 문장을 기반으로, CLAP 모델이 이해하기 쉬운 짧은 영어 음악 묘사를 3개로 다양하게 생성해줘.
    # 문장: “쓸쓸하면서도 희망적인 느낌의 클래식 곡 추천”
    # → Output style: 
    #     1. melancholic classical piano piece
    #     2. hopeful orchestral track with soft strings
    #     3. emotional neoclassical piece with a gentle tone
    # _gemma_prompt = f'''
    # 사용자의 음악 검색을 위한 텍스트를 줄게. 1단계, 2단계에 맞게 작업을 해서 문자열 하나만 반환해. 
    #     1단계: 주어진 입력 텍스트를 영어로 번역해.
    #     2단계: 1단계에서 영어로 번역된 문장을 CLAP(Contrastive Language-Audio Pre-training)의 텍스트 임베딩을 위해서 문장 내용을 분석해서 음악적 특성을 추출해줘.
    #     3단계:
    #     ex)
    #         “melancholic classical piano piece”
    #         “ambient electronic music for studying”
    #         “jazzy hip hop beat with soft drums and vinyl crackle”
    #     아래 문장을 기반으로, CLAP 모델이 이해하기 쉬운 짧은 영어 음악 묘사를 1개로 다양하게 생성해줘.
        
    #     최종적으로는 무조건 하나의 문장만 반환해야 해.
    #     입력 텍스트:\n
    # '''
    
    _system_prompt = """
        다음 음악 검색 쿼리를 JSON으로 파싱하고, CLAP 임베딩용 텍스트도 생성해주세요.

        규칙:
        - artist: 아티스트명 배열
        - title: 곡명 배열
        - genre: 장르 배열  
        - mood: 분위기 배열
        - popular: 유명함 배열 (맥락상 popular 정렬이 필요한지)
        - year: 연도 범위
        - context: 상황/맥락 배열
        - vibe: CLAP 임베딩용 영어 텍스트 배열 (genre, mood, context 기반으로 생성)
         *단, 직접적으로 언급된 항목만 채울것
        * 예시) "빅뱅 붉은노을" → {
            "artist": ["빅뱅", "BIGBANG"],
            "title" : ["붉은노을"]
        }

        CLAP 텍스트 생성 규칙:
        - mood/genre를 구체적인 음악 설명으로 변환
        - 상황/맥락을 음악적 특성으로 표현
        - 3개의 다양한 표현 생성

        예시:
        1. "뉴진스 같은 Y2K 느낌 노래"
        → {
        "artist": ["뉴진스", "NewJeans"],
        "title": [],
        "genre": ["pop"],
        "mood": ["nostalgic", "retro"],
        "popular": [False],
        "year": [2000, 2010],
        "context": ["y2k"],
        "vibe": ["nostalgic pop music", "retro style song", "y2k pop track", "early 2000s pop music", "teen pop ballad"]
        }

        2. "비 오는 날 듣기 좋은 잔잔한 유명한 노래"
        → {
        "artist": [],
        "title": [],
        "genre": ["ballad"],
        "mood": ["calm", "melancholy"],
        "popular": [True],
        "year": [],
        "context": ["rain", "relaxing"],
        "vibe": ["calm ballad", "melancholic song", "rainy day music", "soft acoustic music", "peaceful slow song"]
        }

        3. "운동할 때 신나는 댄스 음악"
        → {
        "artist": [],
        "title": [],
        "genre": ["dance"],
        "mood": ["energetic", "exciting"],
        "popular": [False],
        "year": [],
        "context": ["workout"],
        "vibe": ["energetic dance music", "upbeat workout song", "high energy electronic music", "fast tempo dance track", "gym motivation music"]
        }

        4. ""(비어있는 경우)
        → {
        "artist": [],
        "title": [],
        "genre": [],
        "mood": [],
        "popular": [False],
        "year": [],
        "context": [],
        "vibe": []
        }

        반드시 JSON 형식으로만 응답하세요.
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
        "temperature": 0.1,
        "response_format": {"type": "json_object"}  # JSON 응답 강제 (지원되면)
    }

    @staticmethod
    def get_request(text):          
        MuseLLM._gemma_payload['messages'][1]['content'] = f'''쿼리: {text}'''

        response = requests.post(MuseLLM._gemma_url, json= MuseLLM._gemma_payload)

        # 응답 파싱
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
            # corrected_text = response.json().get("text")  # 또는 "response", "result" 등 API 응답 형식에 따라
            # print("교정된 문장:", corrected_text)
        else:
            print("오류:", response.status_code, response.text)
            return None

