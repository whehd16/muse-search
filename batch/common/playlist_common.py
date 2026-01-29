from common.mysql_common import Database
from common.redis_common import RedisClient
import logging
import time
from typing import List, Dict, Tuple

class PlaylistLoader:
    """Program별 Playlist 데이터를 Redis에 캐싱"""

    _table_mapping = {
        'artist': 'muse.tb_embedding_bgem3_artist_h',
        'album_name': 'muse.tb_embedding_bgem3_album_name_h',
        'title': 'muse.tb_embedding_bgem3_song_name_h',
        'vibe': 'muse.tb_embedding_clap_h',
        'lyrics': 'muse.tb_embedding_bgem3_lyrics_slide_h',
        'lyrics_3': 'muse.tb_embedding_bgem3_lyrics_3_slide_h',
        'lyrics_summary': 'muse.tb_embedding_clap_lyrics_summary_h'
    }

    _column_mapping = {
        'artist': ['disccommseq', 'trackno'],
        'album_name': ['disccommseq'],
        'title': ['disccommseq', 'trackno'],
        'vibe': ['disccommseq', 'trackno'],
        'lyrics': ['disccommseq', 'trackno'],
        'lyrics_3': ['disccommseq', 'trackno'],
        'lyrics_summary': ['disccommseq', 'trackno']
    }

    @staticmethod
    def load_all_programs_to_redis():
        """
        모든 program의 include_ids를 Redis에 캐싱 (영구 저장)

        Flow:
            1. mysql_backup에서 모든 program_id 조회
            2. 각 program별로:
               a. mysql_backup에서 곡 정보 조회
               b. 각 테이블(vibe, title, artist...)별로 idx 조회
               c. Redis에 영구 저장
        """
        start_time = time.time()
        logging.info("=" * 80)
        logging.info("Starting playlist cache loading to Redis")
        logging.info("=" * 80)

        # 1. 모든 program_id 조회
        program_ids = Database.get_all_program_ids()

        if not program_ids:
            logging.error("No programs found!")
            return

        logging.info(f"Found {len(program_ids)} programs to process")

        success_count = 0
        fail_count = 0

        # 2. 각 program 처리
        for idx, program_id in enumerate(program_ids, 1):
            try:
                logging.info(f"\n[{idx}/{len(program_ids)}] Processing program_id: {program_id}")
                PlaylistLoader._process_program(program_id)
                success_count += 1
            except Exception as e:
                logging.error(f"Failed to process program_id {program_id}: {e}")
                fail_count += 1

        # 3. 완료
        elapsed_time = time.time() - start_time
        logging.info("=" * 80)
        logging.info(f"Playlist cache loading completed!")
        logging.info(f"Success: {success_count}, Failed: {fail_count}")
        logging.info(f"Total time: {elapsed_time:.2f}s")
        logging.info("=" * 80)

    @staticmethod
    def _process_program(program_id: str):
        """
        특정 program의 모든 테이블별 include_ids를 Redis에 저장 (영구 저장)

        Args:
            program_id: 프로그램 ID
        """
        # 1. mysql_backup에서 곡 정보 조회
        songs = Database.get_program_songs(program_id)

        if not songs:
            logging.warning(f"No songs found for program_id: {program_id}")
            return

        logging.info(f"  → {len(songs)} songs found")

        # 2. 각 테이블별로 처리
        for key in PlaylistLoader._table_mapping.keys():
            try:
                include_ids = PlaylistLoader._get_include_ids_for_key(key, songs)
                # include_ids = [i for i in range(1,100)]
                if include_ids:
                    # Redis에 영구 저장
                    
                    RedisClient.set_playlist_include_ids(key, program_id, include_ids)
                    logging.info(f"  → [{key}] {len(include_ids)} idx saved to Redis")
                else:
                    logging.warning(f"  → [{key}] No idx found")

            except Exception as e:
                logging.error(f"  → [{key}] Error: {e}")

        # 3. 갱신 시간 저장
        RedisClient.set_last_update_time(program_id, time.time())

    @staticmethod
    def _get_include_ids_for_key(key: str, songs: List[Dict], batch_size: int = 50000) -> List[int]:
        """
        특정 key(테이블)의 include_ids 조회

        Args:
            key: 테이블 타입 (vibe, title, artist...)
            songs: [{'disc_comm_seq': 12345, 'track_no': '01'}, ...]
            batch_size: 배치 크기

        Returns:
            FAISS idx 리스트
        """
        if not songs:
            return []
        
        disc_track_pairs = [
            (song['disc_comm_seq'].strip(), song['track_no'].strip())
            for song in songs
        ]

        columns = PlaylistLoader._column_mapping.get(key, [])
        include_ids = []

        # 배치로 나눠서 조회
        for i in range(0, len(disc_track_pairs), batch_size):
            batch = disc_track_pairs[i:i + batch_size]
            batch_ids = PlaylistLoader._get_idx_batch(key, batch, columns)
            include_ids.extend(batch_ids)

        return include_ids

    @staticmethod
    def _get_idx_batch(key: str, disc_track_pairs: List[Tuple], columns: List[str]) -> List[int]:
        """
        배치 단위로 idx 조회 (MySQL primary에서)

        Args:
            key: 테이블 타입
            disc_track_pairs: [(disccommseq, trackno), ...]
            columns: 컬럼 리스트

        Returns:
            FAISS idx 리스트
        """
        if not disc_track_pairs:
            return []

        try:
            table = PlaylistLoader._table_mapping[key]

            if 'trackno' in columns:
                # disccommseq와 trackno 둘 다 필요
                placeholders = ", ".join(["(%s, %s)"] * len(disc_track_pairs))
                query = f"""
                    SELECT idx
                    FROM {table}
                    WHERE (disccommseq, trackno) IN ({placeholders})
                """
                params = [item for pair in disc_track_pairs for item in pair]
            else:
                # disccommseq만 필요 (album_name)
                placeholders = ", ".join(["%s"] * len(disc_track_pairs))
                query = f"""
                    SELECT idx
                    FROM {table}
                    WHERE disccommseq IN ({placeholders})
                """
                params = [pair[0] for pair in disc_track_pairs]

            results, code = Database.execute_query(query, params=params, fetchall=True)

            if code == 200:
                # MySQL idx → FAISS idx 변환 (1부터 시작 → 0부터 시작)
                return [row[0] - 1 for row in results]
            else:
                return []

        except Exception as e:
            logging.error(f"PlaylistLoader._get_idx_batch error: {e}")
            return []
