import requests
import copy

class MuseLLM:
    _gemma_url = "http://ai-int.mbc.co.kr:8000/v1/chat/completions" 
    
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
        "title": ["비 오는 날 듣기 좋은 잔잔한 유명한 노래"],
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
        "title": ["운동할 때 신나는 댄스 음악"],
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

        5. artist, title 판단이 어려운 경우 (artist, title 리스트에 그냥 넣을 것) 
        
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
    def make_system_reason_prompt(text, total_results, rank=5):
        return f"""
        아래는 사용자의 음악 검색 요청에 대한 결과입니다. 
        자연스럽고 친근한 응답으로 음악을 추천해주세요.

        사용자 요청: {text}

        검색 결과:
        - 찾은 노래 수: {len(total_results['results'])}개
        - 인기도 필터: {'인기곡 위주' if total_results['popular'] else 
        '전체 범위'}
        - 연도 필터: {', '.join(total_results['year_list']) if 
        total_results['year_list'] else '전체 기간'}

        상위 추천곡:
        {MuseLLM.format_songs(total_results['results'][:rank])}

        요청사항:
        1. 사용자의 요청과 가장 관련성이 높은 선별하여 추천(주어진 곡대로 전부 줄 것, 단 최대 5개)
        2. 각 곡에 대해 왜 추천하는지 간단한 설명 추가        
        3. 자연스러운 대화체로 응답
        4. response 값에 리스트("[,,,,]")안에 이유(description)만 담아서 반환할 것.(파싱해서 써야하기 때문에 리스트 반환 필수,[이유1, 이유2, 이유3, ...]) 
    """

    @staticmethod
    def make_system_reason_payload(prompt):
        return {
        "model": "google/gemma-3-27b-it",
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
        
    @staticmethod
    def get_reason(text, total_results, rank=5):
        response = requests.post(MuseLLM._gemma_url, json= MuseLLM.make_system_reason_payload(prompt=MuseLLM. make_system_reason_prompt(text=text, total_results=total_results, rank=rank)))
        # 응답 파싱
        if response.status_code == 200:
            data = response.json()            
            return data['choices'][0]['message']['content']            
        else:
            print("오류:", response.status_code, response.text)
            return None

    @staticmethod
    def format_songs(songs):
      return '\n'.join([f"- {s['artist']} - {s['song_name']} (매칭도: {1-s['dis']:.2f})"
          for s in songs
      ])
