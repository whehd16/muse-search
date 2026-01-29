# MUSE Search Batch

MUSE Search 시스템의 배치 처리 모듈입니다. FAISS 인덱스 생성/업데이트 및 플레이리스트 캐싱 기능을 제공합니다.

## 목차

- [기능](#기능)
- [디렉토리 구조](#디렉토리-구조)
- [설치 및 실행](#설치-및-실행)
- [배치 명령어](#배치-명령어)
- [자동화 스케줄링](#자동화-스케줄링)
- [설정](#설정)

## 기능

- **FAISS 인덱스 학습**: 초기 클러스터 인덱스 생성
- **FAISS 인덱스 구축**: 전체 벡터 데이터를 인덱스에 추가
- **일일 인덱스 업데이트**: 신규 벡터만 증분 추가
- **플레이리스트 캐싱**: Redis에 프로그램별 플레이리스트 캐싱

## 디렉토리 구조

```
batch/
├── muse.py                      # 메인 배치 스크립트
├── config.py                    # 설정 (DB, 캐시)
├── common/
│   ├── faiss_common.py          # FAISS 인덱스 생성/학습
│   ├── dataloader_common.py     # 벡터/임베딩 데이터 로드
│   ├── playlist_common.py       # 플레이리스트 캐싱
│   ├── mysql_common.py          # MySQL 커넥션
│   ├── mysql_backup_common.py   # 백업 MySQL 접근
│   ├── redis_common.py          # Redis 캐싱
│   └── logger_common.py         # 로깅
├── script/
│   ├── train_faiss.sh           # 초기 FAISS 학습 스크립트
│   ├── add_faiss.sh             # 전체 인덱스 구축 스크립트
│   └── add_daily_faiss.sh       # 일일 증분 업데이트 스크립트
└── logs/
    ├── train_faiss/             # 학습 로그
    ├── add_faiss/               # 인덱스 구축 로그
    ├── add_daily_faiss/         # 일일 업데이트 로그
    └── cache_playlist/          # 플레이리스트 캐싱 로그
```

## 설치 및 실행

### 운영 환경

- **서버**: 10.152.141.121 (Ubuntu)
- **경로**: `/data1/muse-search/batch`
- **Python 환경**: `/home/miniconda3/envs/muse-search`

### 실행 환경 설정

```bash
# conda 환경 활성화
conda activate muse-search

# 작업 디렉토리 이동
cd /data1/muse-search/batch
```

## 배치 명령어

### 1. train_faiss - FAISS 인덱스 학습

초기 FAISS IVF-PQ 클러스터 구조를 생성합니다.

```bash
python muse.py train_faiss \
  --model {clap|bgem3} \
  --type {song|lyrics_summary|artist|song_name|album_name|lyrics_slide|lyrics_3_slide} \
  --output <출력_인덱스_경로> \
  --dimension {512|1024}
```

**옵션 설명:**
| 옵션 | 설명 |
|------|------|
| `--model` | 임베딩 모델 (clap: 512D, bgem3: 1024D) |
| `--type` | 인덱스 타입 |
| `--output` | 출력 인덱스 파일 경로 |
| `--dimension` | 벡터 차원 |

**예시:**
```bash
# CLAP vibe 인덱스 학습
python muse.py train_faiss \
  --model clap \
  --type song \
  --output ./index/muse_vibe_cluster.index \
  --dimension 512

# BGE-M3 artist 인덱스 학습
python muse.py train_faiss \
  --model bgem3 \
  --type artist \
  --output ./index/muse_artist_cluster.index \
  --dimension 1024
```

### 2. add_faiss - 전체 벡터 추가

학습된 클러스터에 모든 벡터를 추가합니다.

```bash
python muse.py add_faiss \
  --model {clap|bgem3} \
  --type {song|lyrics_summary|artist|song_name|album_name|lyrics_slide|lyrics_3_slide} \
  --input <학습된_클러스터_인덱스> \
  --output <최종_인덱스_경로> \
  --dimension {512|1024}
```

**예시:**
```bash
# CLAP vibe 인덱스 구축
python muse.py add_faiss \
  --model clap \
  --type song \
  --input ./index/muse_vibe_cluster.index \
  --output ./index/muse_vibe.index \
  --dimension 512
```

### 3. add_daily_faiss - 일일 증분 업데이트

기존 인덱스에 신규 벡터만 추가합니다.

```bash
python muse.py add_daily_faiss \
  --model {clap|bgem3} \
  --type {song|lyrics_summary|artist|song_name|album_name|lyrics_slide|lyrics_3_slide} \
  --input <기존_인덱스> \
  --output <업데이트된_인덱스_경로> \
  --dimension {512|1024}
```

**예시:**
```bash
# 일일 vibe 인덱스 업데이트
python muse.py add_daily_faiss \
  --model clap \
  --type song \
  --input /data1/muse-search/server/app/files/index/muse_vibe.index \
  --output ./index/muse_vibe_$(date +%Y%m%d).index \
  --dimension 512
```

### 4. info_faiss - 인덱스 정보 조회

인덱스의 메타데이터를 확인합니다.

```bash
python muse.py info_faiss \
  --input <인덱스_경로> \
  --dimension {512|1024}
```

**출력 정보:**
- `nlist`: 클러스터 수
- `is_trained`: 학습 완료 여부
- `ntotal`: 총 벡터 수
- `d`: 벡터 차원

**예시:**
```bash
python muse.py info_faiss \
  --input ./index/muse_vibe.index \
  --dimension 512

# 출력 예시:
# nlist: 1000
# is_trained: True
# ntotal: 500000
# d: 512
```

### 5. cache_playlist - 플레이리스트 캐싱

모든 프로그램의 플레이리스트를 Redis에 캐싱합니다.

```bash
python muse.py cache_playlist
```

**캐싱 대상 프로그램:**
- `drp` - 드라이브 뮤직
- `fgy` - FM4U 굿모닝
- `k2k` - 키스더라디오
- `mdi` - 매일밤 음악여행
- `nmg` - 남녀뮤직
- `rtc` - 라디오텔레콤

**Redis 키 패턴:** `playlist_idx:{program_id}_{index_type}`

## 자동화 스케줄링

### Cron 설정 (운영 환경)

일일 인덱스 업데이트가 cron으로 자동 실행됩니다.

```bash
# crontab -e
58 16 * * * cd /data1/muse-search/batch/script && ./add_daily_faiss.sh
```

**스케줄 설명:**
- 매일 16:58 실행
- 7개 인덱스 모두 증분 업데이트
- 서버 인덱스 파일 자동 교체

### Shell 스크립트

#### train_faiss.sh - 초기 학습 (수동 실행)

7개 인덱스 타입 전체를 학습합니다.

```bash
cd /data1/muse-search/batch/script
./train_faiss.sh
```

**학습 대상:**
| 타입 | 모델 | 차원 |
|------|------|------|
| vibe | CLAP | 512 |
| lyrics_summary | CLAP | 512 |
| artist | BGE-M3 | 1024 |
| title | BGE-M3 | 1024 |
| album_name | BGE-M3 | 1024 |
| lyrics | BGE-M3 | 1024 |
| lyrics_3 | BGE-M3 | 1024 |

#### add_faiss.sh - 전체 구축 (수동 실행)

학습된 클러스터에 모든 벡터를 추가합니다.

```bash
cd /data1/muse-search/batch/script
./add_faiss.sh
```

#### add_daily_faiss.sh - 일일 업데이트 (자동 실행)

신규 벡터만 증분 추가하고 서버에 배포합니다.

```bash
cd /data1/muse-search/batch/script
./add_daily_faiss.sh
```

**처리 순서:**
1. DB에서 신규 벡터 확인 (FAISS ntotal vs DB max idx)
2. 신규 벡터를 인덱스에 추가
3. 날짜 suffix로 인덱스 저장 (예: `muse_vibe_20241128.index`)
4. 기존 서버 인덱스 백업
5. 신규 인덱스를 서버 디렉토리에 복사

## 설정

### config.py

```python
# MySQL (임베딩 데이터)
DATABASE_CONFIG = {
    'host': '10.152.75.171',
    'user': 'muse',
    'password': '********',
    'database': 'muse',
}

# MySQL 백업 (플레이리스트 데이터)
DATABASE_BACKUP_CONFIG = {
    'host': '10.63.57.193',
    'user': 'muse',
    'password': '********',
    'database': 'muse',
}

# Redis (플레이리스트 캐시)
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}

# 대상 프로그램 목록
PROGRAM_ID = ['drp', 'fgy', 'k2k', 'mdi', 'nmg', 'rtc']
```

### 임베딩 테이블 매핑

| 타입 | 테이블명 |
|------|----------|
| clap_song (vibe) | tb_embedding_clap_h |
| clap_lyrics_summary | tb_embedding_clap_lyrics_summary_h |
| bgem3_artist | tb_embedding_bgem3_artist_h |
| bgem3_song_name (title) | tb_embedding_bgem3_song_name_h |
| bgem3_album_name | tb_embedding_bgem3_album_name_h |
| bgem3_lyrics_slide | tb_embedding_bgem3_lyrics_slide_h |
| bgem3_lyrics_3_slide | tb_embedding_bgem3_lyrics_3_slide_h |

## 배치 프로세스 플로우

### 일일 업데이트 플로우

```
add_daily_faiss.sh 실행 (cron: 매일 16:58)
        │
        ▼
┌─────────────────────────────────────────┐
│ 각 인덱스 타입별 반복 처리               │
│ (vibe, lyrics_summary, artist, title,   │
│  album_name, lyrics, lyrics_3)          │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ MuseDataLoader.get_last_idx()           │
│ → DB 최대 인덱스 확인                    │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ MuseFaiss.read_index()                  │
│ → 기존 서버 인덱스 로드                  │
│ → 현재 인덱스 벡터 수 (ntotal) 확인      │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ 신규 벡터 존재 여부 확인                 │
│ (DB max idx > FAISS ntotal)             │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ MuseDataLoader.get_add_vectors()        │
│ → 신규 벡터 배치 로드 (5000개 단위)      │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ MuseFaiss.add()                         │
│ → 인덱스에 벡터 추가                     │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ MuseFaiss.write_index()                 │
│ → 날짜 suffix로 인덱스 저장              │
│   (muse_vibe_20241128.index)            │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ 서버 배포                                │
│ 1. 기존 서버 인덱스 백업                 │
│ 2. 신규 인덱스를 서버 디렉토리에 복사     │
└─────────────────────────────────────────┘
```

### 플레이리스트 캐싱 플로우

```
cache_playlist 실행
        │
        ▼
┌─────────────────────────────────────────┐
│ 각 프로그램별 처리                       │
│ (drp, fgy, k2k, mdi, nmg, rtc)          │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ PlaylistDAO.get_playlist_info()         │
│ → tb_song_{program_id}_m 에서 곡 조회    │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ SearchDAO.get_playlist_idx()            │
│ → 각 인덱스 타입별 FAISS idx 조회        │
└─────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│ RedisClient.set_playlist_include_ids()  │
│ → Redis에 영구 저장                      │
│ → 키: playlist_idx:{program}_{type}     │
└─────────────────────────────────────────┘
```

## 로그

로그 파일 위치: `./logs/{작업명}/`

```bash
# 일일 업데이트 로그 확인
tail -f logs/add_daily_faiss/add_daily_faiss_$(date +%Y%m%d).log

# 플레이리스트 캐싱 로그 확인
tail -f logs/cache_playlist/cache_playlist_$(date +%Y%m%d).log
```

## 트러블슈팅

### 인덱스 업데이트 실패

1. DB 연결 확인
```bash
mysql -h 10.152.75.171 -u muse -p muse
```

2. 기존 인덱스 파일 존재 확인
```bash
ls -la /data1/muse-search/server/app/files/index/
```

3. 디스크 공간 확인
```bash
df -h /data1
```

### Redis 캐싱 실패

1. Redis 서버 상태 확인
```bash
redis-cli ping
```

2. 메모리 사용량 확인
```bash
redis-cli info memory
```

### 수동 인덱스 복구

인덱스가 손상된 경우 전체 재구축:

```bash
# 1. 클러스터 학습
./train_faiss.sh

# 2. 전체 벡터 추가
./add_faiss.sh

# 3. 서버에 수동 복사
cp ./index/muse_*.index /data1/muse-search/server/app/files/index/

# 4. 서버 재시작
sudo systemctl restart muse-search
```
