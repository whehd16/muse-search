#!/bin/bash
set -euo pipefail

cd /data1/muse-search/batch

INDEX_DIR="/data1/muse-search/batch/index/prod"
SERVER_DIR="/data1/muse-search/server/app/files/index"
TODAY="$(date +%Y%m%d)"

# server 쪽 index 백업 + 배치 최신본 복사
sync_server() {
    local base="$1"  # e.g. muse_vibe, muse_artist ...

    local server_file="${SERVER_DIR}/${base}.index"
    local server_backup="${SERVER_DIR}/${base}_backup.index"
    local batch_file="${INDEX_DIR}/${base}.index"

    # 기존 서버 index 백업 (있을 때만)
    if [ -f "$server_file" ]; then
        echo "[SERVER BACKUP] $server_file -> $server_backup"
        mv -f "$server_file" "$server_backup"
    else
        echo "[SERVER BACKUP] $server_file 없음 → 백업 생략"
    fi

    echo "[SERVER UPDATE] $batch_file -> $server_file"
    cp -f "$batch_file" "$server_file"
}

# ----------------------------------
# CLAP - SONG
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=clap \
    --type=song \
    --input="${INDEX_DIR}/muse_vibe.index" \
    --output="${INDEX_DIR}/muse_vibe_${TODAY}.index" \
    --dimension=512

cp -f "${INDEX_DIR}/muse_vibe_${TODAY}.index" "${INDEX_DIR}/muse_vibe.index"
sync_server "muse_vibe"


# ----------------------------------
# CLAP - LYRICS SUMMARY
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=clap \
    --type=lyrics_summary \
    --input="${INDEX_DIR}/muse_lyrics_summary.index" \
    --output="${INDEX_DIR}/muse_lyrics_summary_${TODAY}.index" \
    --dimension=512

cp -f "${INDEX_DIR}/muse_lyrics_summary_${TODAY}.index" "${INDEX_DIR}/muse_lyrics_summary.index"
sync_server "muse_lyrics_summary"


# ----------------------------------
# BGE-M3 - ARTIST
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=bgem3 \
    --type=artist \
    --input="${INDEX_DIR}/muse_artist.index" \
    --output="${INDEX_DIR}/muse_artist_${TODAY}.index" \
    --dimension=1024

cp -f "${INDEX_DIR}/muse_artist_${TODAY}.index" "${INDEX_DIR}/muse_artist.index"
sync_server "muse_artist"


# ----------------------------------
# BGE-M3 - SONG NAME
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=bgem3 \
    --type=song_name \
    --input="${INDEX_DIR}/muse_title.index" \
    --output="${INDEX_DIR}/muse_title_${TODAY}.index" \
    --dimension=1024

cp -f "${INDEX_DIR}/muse_title_${TODAY}.index" "${INDEX_DIR}/muse_title.index"
sync_server "muse_title"


# ----------------------------------
# BGE-M3 - ALBUM NAME
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=bgem3 \
    --type=album_name \
    --input="${INDEX_DIR}/muse_album_name.index" \
    --output="${INDEX_DIR}/muse_album_name_${TODAY}.index" \
    --dimension=1024

cp -f "${INDEX_DIR}/muse_album_name_${TODAY}.index" "${INDEX_DIR}/muse_album_name.index"
sync_server "muse_album_name"


# ----------------------------------
# BGE-M3 - LYRICS SLIDE
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=bgem3 \
    --type=lyrics_slide \
    --input="${INDEX_DIR}/muse_lyrics.index" \
    --output="${INDEX_DIR}/muse_lyrics_${TODAY}.index" \
    --dimension=1024

cp -f "${INDEX_DIR}/muse_lyrics_${TODAY}.index" "${INDEX_DIR}/muse_lyrics.index"
sync_server "muse_lyrics"


# ----------------------------------
# BGE-M3 - LYRICS 3 SLIDE
# ----------------------------------
/home/miniconda3/envs/muse-search/bin/python muse.py add_daily_faiss \
    --model=bgem3 \
    --type=lyrics_3_slide \
    --input="${INDEX_DIR}/muse_lyrics_3.index" \
    --output="${INDEX_DIR}/muse_lyrics_3_${TODAY}.index" \
    --dimension=1024

cp -f "${INDEX_DIR}/muse_lyrics_3_${TODAY}.index" "${INDEX_DIR}/muse_lyrics_3.index"
sync_server "muse_lyrics_3"

echo "[DONE] batch & server index 모두 갱신 완료"
