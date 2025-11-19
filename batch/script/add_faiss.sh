#!/bin/bash
cd /data1/muse-search/batch

# 인덱스 전부 추가(CLAP)
# 1. tb_embedding_clap_h
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=clap --type=song --input=./index/cluster/clap_vibe_cluster.index --output=./index/dev/muse_vibe.index --dimension=512
# 2. tb_embedding_clap_lyrics_summary_h
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=clap --type=lyrics_summary --input=./index/cluster/clap_lyrics_summary_cluster.index --output=./index/dev/muse_lyrics_summary.index --dimension=512

# 인덱스 전부 추가(BGE-M3)
# 1. tb_embedding_bgem3_artist_h
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=bgem3 --type=artist --input=./index/cluster/bgem3_artist_cluster.index --output=./index/dev/muse_artist.index --dimension=1024
# 2. tb_embedding_bgem3_song_name_h
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=bgem3 --type=song_name --input=./index/cluster/bgem3_song_name_cluster.index --output=./index/dev/muse_title.index --dimension=1024
# 3. tb_embedding_bgem3_album_name_h  
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=bgem3 --type=album_name --input=./index/cluster/bgem3_album_name_cluster.index --output=./index/dev/muse_album_name.index --dimension=1024
# 4. tb_embedding_bgem3_lyrics_slide_h  
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=bgem3 --type=lyrics_slide --input=./index/cluster/bgem3_lyrics_cluster.index --output=./index/dev/muse_lyrics.index --dimension=1024
# 5. tb_embedding_bgem3_lyrics_3_slide_h  
/home/miniconda3/envs/muse-search/bin/python muse.py add_faiss --model=bgem3 --type=lyrics_3_slide --input=./index/cluster/bgem3_lyrics_3_cluster.index --output=./index/dev/muse_lyrics_3.index --dimension=1024