# MUSE Search Server

MUSE Search는 음악 검색을 위한 FastAPI 기반 API 서버입니다. FAISS 벡터 검색, LLM 기반 쿼리 이해, 다중 임베딩 모델을 활용하여 지능형 음악 검색 기능을 제공합니다.

## 목차

- [기능](#기능)
- [아키텍처](#아키텍처)
- [디렉토리 구조](#디렉토리-구조)
- [설치 및 실행](#설치-및-실행)
- [API 엔드포인트](#api-엔드포인트)
- [설정](#설정)
- [의존성](#의존성)

## 기능

- **텍스트 기반 음악 검색**: 자연어 쿼리로 음악 검색
- **플레이리스트 내 검색**: 특정 플레이리스트 범위 내에서 검색
- **유사 곡 추천**: 분위기(vibe) 또는 가사(lyrics) 기반 유사곡 검색
- **LLM 쿼리 분석**: 자연어 쿼리를 아티스트, 제목, 장르, 분위기 등으로 분류
- **다중 인덱스 검색**: artist, title, album, vibe, lyrics 등 7개 인덱스 병렬 검색

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Request                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   SearchController                        │   │
│  │  /search/text, /search/similar, /search/analyze ...     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        SearchService                             │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐    │
│  │   MuseLLM    │  │ FaissService  │  │ EmbeddingService │    │
│  │ (쿼리 분석)   │  │ (벡터 검색)    │  │  (임베딩 생성)    │    │
│  └──────────────┘  └───────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   FAISS Index   │  │     MySQL       │  │     Oracle      │
│  (벡터 저장소)    │  │  (임베딩 데이터)  │  │   (곡 메타데이터) │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │
          ▼
┌─────────────────┐
│     Redis       │
│ (플레이리스트 캐시)│
└─────────────────┘
```

## 디렉토리 구조

```
server/app/
├── main.py                      # FastAPI 애플리케이션 진입점
├── config.py                    # 설정 (DB, 캐시, 경로)
├── controllers/
│   └── search_controller.py     # API 라우트 핸들러
├── services/
│   ├── search_service.py        # 핵심 검색 로직
│   ├── embedding_service.py     # 임베딩 모델 연동
│   └── faiss_service.py         # FAISS 인덱스 래퍼
├── daos/
│   ├── search_dao.py            # 검색 DB 쿼리
│   └── playlist_dao.py          # 플레이리스트 데이터 접근
├── common/
│   ├── faiss_common.py          # FAISS 인덱스 로드/관리
│   ├── redis_common.py          # Redis 캐싱 클라이언트
│   ├── llm_common.py            # LLM 연동 (쿼리 이해)
│   ├── oracle_common.py         # Oracle DB 커넥션 풀
│   ├── mysql_common.py          # MySQL 커넥션
│   ├── mysql_backup_common.py   # MySQL 백업 DB 접근
│   ├── logger_common.py         # 로깅 유틸리티
│   └── response_common.py       # API 응답 포맷팅
├── files/index/                 # FAISS 인덱스 파일
├── logs/                        # 애플리케이션 로그
└── oracle/                      # Oracle 클라이언트 라이브러리
```

## 설치 및 실행

### 운영 환경

- **서버**: 10.152.141.121 (Ubuntu)
- **경로**: `/data1/muse-search/server/app`
- **Python 환경**: `/home/miniconda3/envs/muse-search`
- **포트**: 13373

### systemd 서비스 설정

서비스 파일 위치: `/etc/systemd/system/muse-search.service`

```ini
[Unit]
Description=FastAPI application
After=network.target

[Service]
WorkingDirectory=/data1/muse-search/server/app
Environment="LD_LIBRARY_PATH=/data1/muse-search/server/app/oracle/instantclient_21_17:"
Environment="PYTHONPATH=/data1/muse-search/server/app"
ExecStart=/home/miniconda3/envs/muse-search/bin/gunicorn main:app -w 32 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:13373
Restart=always

[Install]
WantedBy=multi-user.target
```

### 서비스 관리 명령어

```bash
# 서비스 시작
sudo systemctl start muse-search

# 서비스 중지
sudo systemctl stop muse-search

# 서비스 재시작
sudo systemctl restart muse-search

# 서비스 상태 확인
sudo systemctl status muse-search

# 부팅 시 자동 시작 설정
sudo systemctl enable muse-search

# 로그 확인
sudo journalctl -u muse-search -f
```

### 로컬 개발 환경 실행

```bash
cd server/app
uvicorn main:app --reload --host 0.0.0.0 --port 13373
```

## API 엔드포인트

### 1. 텍스트 검색

**POST** `/search/text`

자연어 쿼리로 음악을 검색합니다.

```json
// Request
{
  "text": "비오는 날 듣기 좋은 재즈",
  "mood": ["calm", "romantic"],
  "vibe_only": false
}

// Response
{
  "status": "success",
  "data": {
    "results": [
      {
        "disccommseq": "12345",
        "trackno": "1",
        "artist": "Artist Name",
        "title": "Song Title",
        "album": "Album Name",
        "distance": 0.234,
        ...
      }
    ]
  }
}
```

### 2. 플레이리스트 내 검색

**POST** `/search/text_playlist`

특정 플레이리스트 범위 내에서 검색합니다.

```json
// Request
{
  "text": "신나는 댄스곡",
  "mood": [],
  "playlist_id": "drp",
  "vibe_only": false
}
```

### 3. 유사곡 검색 (분위기 기반)

**POST** `/search/similar`

특정 곡과 분위기가 유사한 곡을 찾습니다.

```json
// Request
{
  "disccommseq": "12345",
  "trackno": "1"
}
```

### 4. 플레이리스트 내 유사곡 검색

**POST** `/search/similar_in_playlist`

특정 플레이리스트 내에서 유사곡을 찾습니다.

```json
// Request
{
  "disccommseq": "12345",
  "trackno": "1",
  "playlist_id": "drp"
}
```

### 5. 유사곡 검색 (가사 기반)

**POST** `/search/similar_lyric`

가사가 유사한 곡을 찾습니다.

```json
// Request
{
  "disccommseq": "12345",
  "trackno": "1"
}
```

### 6. 플레이리스트 내 가사 유사곡 검색

**POST** `/search/similar_lyric_in_playlist`

```json
// Request
{
  "disccommseq": "12345",
  "trackno": "1",
  "playlist_id": "drp"
}
```

### 7. 검색 결과 분석

**POST** `/search/analyze`

검색 결과가 왜 매칭되었는지 분석합니다.

```json
// Request
{
  "text": "검색 쿼리",
  "llm_result": { ... },
  "disccommseq": "12345",
  "trackno": "1"
}
```

## 설정

### 데이터베이스 설정 (`config.py`)

```python
# MySQL (임베딩 데이터)
DATABASE_CONFIG = {
    'host': '10.152.75.171',
    'user': 'muse',
    'password': '********',
    'database': 'muse',
}

# Oracle (곡 메타데이터)
ORACLE_DATABASE_CONFIG = {
    'host': '203.238.229.106',
    'port': 1521,
    'service_name': 'ORA1a',
    'user_name': 'mbcrnd',
    'password': '********'
}

# Redis (플레이리스트 캐시)
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}
```

### FAISS 인덱스

| 인덱스 타입 | 임베딩 모델 | 차원 | 용도 |
|------------|------------|------|------|
| muse_artist | BGE-M3 | 1024 | 아티스트 검색 |
| muse_album_name | BGE-M3 | 1024 | 앨범명 검색 |
| muse_title | BGE-M3 | 1024 | 곡 제목 검색 |
| muse_vibe | CLAP | 512 | 분위기/상황 검색 |
| muse_lyrics | BGE-M3 | 1024 | 가사 검색 |
| muse_lyrics_3 | BGE-M3 | 1024 | 가사 검색 (3 슬라이드) |
| muse_lyrics_summary | CLAP | 512 | 가사 요약 검색 |

### LLM 쿼리 분류 (Case)

| Case | 설명 | 검색 인덱스 |
|------|------|-----------|
| 0 | 아티스트 검색 | artist |
| 1 | 제목 검색 | title |
| 2 | 아티스트 + 제목 | artist, title |
| 3 | 장르/지역/연도 필터 | vibe |
| 5 | 아티스트 + 분위기 | artist, vibe |
| 6 | 분위기/상황 (운동, 드라이브 등) | vibe |
| 9 | 가사 검색 | lyrics, lyrics_3 |
| 10 | 앨범 검색 | album_name |
| 13 | 긴 텍스트 (라디오 사연, 기사 등) | lyrics_summary |

## 의존성

### 주요 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| fastapi | 0.115.8 | API 프레임워크 |
| uvicorn | - | ASGI 서버 |
| gunicorn | - | 프로세스 관리 |
| faiss-cpu | 1.11.0 | 벡터 유사도 검색 |
| redis | 6.4.0 | 캐시 클라이언트 |
| oracledb | 2.5.1 | Oracle DB 드라이버 |
| pymysql | - | MySQL 드라이버 |
| rapidfuzz | 3.14.1 | 문자열 유사도 |
| numpy | - | 수치 연산 |

### 외부 서비스

| 서비스 | 주소 | 용도 |
|--------|------|------|
| 임베딩 서버 | http://192.168.170.151:13373 | BGE-M3, CLAP 임베딩 생성 |
| LLM 서버 (Gemma) | http://ai-int.mbc.co.kr:8000 | 쿼리 분석 |
| LLM 서버 (OSS) | http://ai-int.mbc.co.kr:9000 | 쿼리 분석 |

## 로그

로그 파일 위치: `./logs/`

```bash
# 로그 실시간 확인
tail -f logs/search_service.log
```

## 트러블슈팅

### Oracle 클라이언트 연결 오류

Oracle Instant Client 경로가 `LD_LIBRARY_PATH`에 설정되어 있는지 확인:

```bash
export LD_LIBRARY_PATH=/data1/muse-search/server/app/oracle/instantclient_21_17:$LD_LIBRARY_PATH
```

### FAISS 인덱스 로드 실패

인덱스 파일이 `./files/index/` 디렉토리에 있는지 확인:

```bash
ls -la ./files/index/
# muse_artist.index
# muse_album_name.index
# muse_title.index
# muse_vibe.index
# muse_lyrics.index
# muse_lyrics_3.index
# muse_lyrics_summary.index
```

### Redis 연결 오류

Redis 서버 상태 확인:

```bash
redis-cli ping
# PONG
```
