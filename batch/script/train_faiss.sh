#!/bin/bash
cd /data1/muse-search/batch

# 클러스터 학습(CLAP)
# 1. tb_embedding_clap_h
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=clap --type=song --output=./index/cluster/clap_vibe_cluster.index --dimension=512
# 2. tb_embedding_clap_lyrics_summary_h
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=clap --type=lyrics_summary --output=./index/cluster/clap_lyrics_summary_cluster.index --dimension=512

# 클러스터 학습(BGE-M3)
# 1. tb_embedding_bgem3_artist_h
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=bgem3 --type=artist --output=./index/cluster/bgem3_artist_cluster.index --dimension=1024
# 2. tb_embedding_bgem3_song_name_h
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=bgem3 --type=song_name --output=./index/cluster/bgem3_song_name_cluster.index --dimension=1024
# 3. tb_embedding_bgem3_album_name_h  
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=bgem3 --type=album_name --output=./index/cluster/bgem3_album_name_cluster.index --dimension=1024
# 4. tb_embedding_bgem3_lyrics_slide_h  
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=bgem3 --type=lyrics_slide --output=./index/cluster/bgem3_lyrics_cluster.index --dimension=1024
# 5. tb_embedding_bgem3_lyrics_3_slide_h  
/home/miniconda3/envs/muse-search/bin/python muse.py train_faiss --model=bgem3 --type=lyrics_3_slide --output=./index/cluster/bgem3_lyrics_3_cluster.index --dimension=1024