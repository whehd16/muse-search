from common.mysql_common import Database
from common.oracle_common import OracleDB
from typing import List, Dict
import logging
import time

class SearchDAO:
    _table_mapping ={
        'artist': 'tb_embedding_bgem3_artist_h',
        'album_name': 'tb_embedding_bgem3_album_name_h',
        'title': 'tb_embedding_bgem3_song_name_h',
        'vibe' : 'tb_embedding_clap_h',
        'lyrics': 'tb_embedding_bgem3_lyrics_slide_h',
        'lyrics_3': 'tb_embedding_bgem3_lyrics_3_slide_h',
        'lyrics_summary': 'tb_embedding_clap_lyrics_summary_h'
    }

    _column_mapping = {
        'artist': ['disccommseq','trackno'],        
        'album_name': ['disccommseq'],
        'title': ['disccommseq','trackno'],
        'vibe' : ['disccommseq','trackno'],
        'lyrics': ['disccommseq','trackno'],
        'lyrics_3': ['disccommseq','trackno'],
        'lyrics_summary': ['disccommseq','trackno']
    }
    
    @staticmethod
    def get_song_batch_info(key: str, idx_list: List):
        batch_info = {}        
        # logging.info(f'''{key}, {idx_list}''')
        results, code = Database.execute_query(f"""
            SELECT idx, disccommseq, trackno
            FROM {SearchDAO._table_mapping[key]}
            WHERE idx in ({','.join(list(map(str, idx_list)))})
        """, fetchall=True)
        if code == 200:
            for result in results:
                batch_info[result[0]] = [{
                    'disccommseq': result[1],
                    'trackno': result[2]
                }]
        return batch_info
    
    @staticmethod
    def get_song_by_album_info(album_info_dict):
        batch_info = {}
        conditions = []
        
        for disccommseq, _ in album_info_dict.items():
            conditions.append(f"(DISC_COMM_SEQ={disccommseq})")
        
        where_clause =" OR ".join(conditions)
        results = OracleDB.execute_query(f"""
            SELECT DISC_COMM_SEQ, TRACK_NO 
            FROM MIBIS.MI_SONG_INFO
            WHERE {where_clause}
        """)
        
        if results:
            for result in results:                
                idx = album_info_dict[result['disc_comm_seq']]['idx']
                
                if idx not in batch_info:
                    batch_info[idx] = []                
                batch_info[idx].append(
                    {
                        'disccommseq' : result['disc_comm_seq'], 
                        'trackno': result['track_no'].strip()
                    }
                )
        return batch_info

    @staticmethod
    def get_album_batch_info(key: str, idx_list: List):
        batch_info = {}   
        # logging.info(f'''{key}, {idx_list}''')
        results, code = Database.execute_query(f"""
            SELECT idx, disccommseq
            FROM {SearchDAO._table_mapping[key]}
            WHERE idx in ({','.join(list(map(str, idx_list)))})
        """, fetchall=True)
        if code == 200:
            for result in results:
                # batch_info[result[0]] = {
                #     'disccommseq': result[1]                    
                # }
                batch_info[result[1]] = {
                    'idx': result[0]
                }
        return batch_info 

    @staticmethod
    def get_song_info(key: str, idx: int) -> Dict:
        result, code = Database.execute_query(f"""
            SELECT disccommseq, trackno
            FROM {SearchDAO._table_mapping[key]}
            WHERE idx = {idx+1}
        """, fetchone=True)
        if code == 200:
            return {
                'disccommseq': result[0], 
                'trackno': result[1]
            }
        else:
            return {}
        
    @staticmethod
    def get_song_clap_embedding(key, disccommseq, trackno):        
        results, code = Database.execute_query(f"""
            SELECT disccommseq, trackno, chunk_num, embedding_result
            FROM {SearchDAO._table_mapping[key]}
            WHERE disccommseq = {disccommseq} AND trackno = '{trackno}'
        """, fetchall=True)
        if code == 200:
            return [ result[3] for result in results ]
        else:
            return []
        
    @staticmethod
    def get_song_clap_lyric_summary(key, disccommseq, trackno):
        results, code = Database.execute_query(f"""
            SELECT disccommseq, trackno, summary_num, embedding_result
            FROM {SearchDAO._table_mapping[key]}
            WHERE disccommseq = {disccommseq} AND trackno = '{trackno}'
        """, fetchall=True)
        if code == 200:
            return [ result[3] for result in results ]
        else:
            return []
        
    @staticmethod
    def get_song_bgem3_song_name(key, disccommseq, trackno):
        results, code = Database.execute_query(f"""
            SELECT disccommseq, trackno, song_name, song_name_embedding
            FROM {SearchDAO._table_mapping[key]}
            WHERE disccommseq = {disccommseq} AND trackno = '{trackno}'
        """, fetchall=True)
        if code == 200:
            return [ result[3] for result in results ]
        else:
            return []

    @staticmethod
    def get_song_batch_meta(disc_track_pairs: List[tuple]):
        if not disc_track_pairs:
            return {}

        conditions = []
        
        for disccommseq, trackno in disc_track_pairs:
            conditions.append(f"(A.DISC_COMM_SEQ={disccommseq} AND A.TRACK_NO='{trackno}')")
        
        where_clause =" OR ".join(conditions)
        results = OracleDB.execute_query(f"""
            SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, 
            B.DISC_NAME, A.DISC_COMM_SEQ, A.TRACK_NO, MASTERING_YEAR, HIT_YEAR, B.DISC_GENRE_TXT,
            C.JPG_FILE_NAME, A.MP3_PATH,
            CASE 
                WHEN A.MP3_PATH IS NULL THEN 0 
                ELSE 1 
            END AS MP3_PATH_FLAG
            FROM MIBIS.MI_SONG_INFO A 
            JOIN MIBIS.MI_DISC_INFO B 
            ON A.DISC_COMM_SEQ = B.DISC_COMM_SEQ
            LEFT JOIN MIBIS.MI_DISC_COMM_INFO C
            ON B.DISC_COMM_SEQ = C.DISC_COMM_SEQ
            WHERE {where_clause}
        """)
        
        if not results:
            return {}
        
        song_meta_dict = {}
        for row in results:
            try:
                row['track_no'] = row['track_no'].strip()
            except:
                pass
            
            key = f'''{row['disc_comm_seq']}_{row['track_no']}'''
            song_meta_dict[key] = row
        return song_meta_dict

    @staticmethod
    def get_song_meta(disccommseq: int, trackno: str) -> Dict:
        result = OracleDB.execute_query(f"""
            SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, B.DISC_NAME, A.DISC_COMM_SEQ, A.TRACK_NO, MASTERING_YEAR, HIT_YEAR, B.DISC_GENRE_TXT,
            C.JPG_FILE_NAME
            FROM MIBIS.MI_SONG_INFO A 
            JOIN MIBIS.MI_DISC_INFO B 
            ON A.DISC_COMM_SEQ = B.DISC_COMM_SEQ
            LEFT JOIN MIBIS.MI_DISC_COMM_INFO C
            ON B.DISC_COMM_SEQ = C.DISC_COMM_SEQ
            WHERE A.DISC_COMM_SEQ={disccommseq} AND A.TRACK_NO='{trackno}'
        """)
        if result:
            try:
                result[0]['track_no'] = result[0]['track_no'].strip()
            except:
                pass
            return result[0]
    
    @staticmethod
    def get_mood_dict():
        results, code = Database.execute_query(f"""
            SELECT eng_mood, kor_mood
            FROM muse.tb_mood_mapping_m            
        """, fetchall=True)
        
        if code == 200:
            return { result[0]: result[1] for result in results }
        else:
            return {}

    @staticmethod
    def get_song_mood_value(disc_track_pairs: List[tuple]):
        if not disc_track_pairs:
            return {}

        # (%s, %s), (%s, %s) 형태의 placeholder 생성
        placeholders = ", ".join(["(%s, %s)"] * len(disc_track_pairs))
        query = f"""
            SELECT disccommseq, trackno, mood_list, arousal, valence
            FROM muse.tb_info_song_mood_h
            WHERE (disccommseq, trackno) IN ({placeholders})
        """
        
        params = [item for pair in disc_track_pairs for item in pair]

        results, code = Database.execute_query(query, params=params, fetchall=True)
        
        if code == 200:
            mood_value_dict = {}
            for result in results:
                key = f"{result[0]}_{result[1]}"
                mood_value_dict[key] = {
                    'mood_list': result[2],
                    'arousal': result[3],
                    'valence': result[4]
                }
            return mood_value_dict
        else:
            return {}
    
    @staticmethod
    def get_song_bpm_value(disc_track_pairs: List[tuple]):
        if not disc_track_pairs:
            return {}
        
        placeholders = ", ".join(["(%s, %s)"] * len(disc_track_pairs))
        query = f"""
            SELECT disccommseq, trackno, bpm
            FROM muse.tb_info_song_bpm_h
            WHERE (disccommseq, trackno) IN ({placeholders})
        """

        params = [item for pair in disc_track_pairs for item in pair]
        results, code = Database.execute_query(query, params, fetchall=True)
        
        if code == 200:
            mood_value_dict = {}
            for result in results:
                key = f"{result[0]}_{result[1]}"
                mood_value_dict[key] = {
                    'bpm': result[2]
                }
            return mood_value_dict
        else:
            return {}
        
    @staticmethod
    def get_song_category():       
        
        results, code = Database.execute_query(f"""
            SELECT region, genre
            FROM muse.tb_info_song_category_m
            WHERE valid=1
        """, fetchall=True)
        
        if code == 200:
            category_dict = {}
            for region, genre in results:
                if region not in category_dict:
                    category_dict[region] = set()
                category_dict[region].add(genre)
            return category_dict
        else:
            return {}
        
    @staticmethod
    def get_song_genre():
        results, code = Database.execute_query(f"""
            SELECT genre
            FROM muse.tb_info_song_category_m
            GROUP BY genre
        """, fetchall=True)

        if code == 200:
            genre_set = set()
            for genre in results:
                genre_set.add(genre[0])
            return genre_set
        else:
            return set()
        

    @staticmethod
    def get_playlist_idx(key: str, disc_track_pairs: List[tuple]) -> List[int]:
        """
        disc_track_pairs로부터 FAISS용 idx 리스트를 조회

        Args:
            key: 테이블 타입 (artist, title, vibe, etc.)
            disc_track_pairs: [(disccommseq, trackno), ...] 형태의 리스트

        Returns:
            FAISS idx 리스트 (MySQL idx - 1)
            예: MySQL idx=[1, 2, 5] → FAISS idx=[0, 1, 4]

        Note:
            MySQL idx는 1부터 시작, FAISS는 0부터 시작하므로 -1 변환
        """
        if not disc_track_pairs:
            return []

        # key에 따라 컬럼 확인 (album_name은 trackno 없음)
        columns = SearchDAO._column_mapping.get(key, [])

        if 'trackno' in columns:
            # disccommseq와 trackno 둘 다 필요
            placeholders = ", ".join(["(%s, %s)"] * len(disc_track_pairs))
            query = f"""
                SELECT idx
                FROM {SearchDAO._table_mapping[key]}
                WHERE (disccommseq, trackno) IN ({placeholders})
            """            
            params = [item for pair in disc_track_pairs for item in pair]
        else:
            # disccommseq만 필요 (album_name)
            placeholders = ", ".join(["%s"] * len(disc_track_pairs))
            query = f"""
                SELECT idx
                FROM {SearchDAO._table_mapping[key]}
                WHERE disccommseq IN ({placeholders})
            """
            # disc_track_pairs에서 disccommseq만 추출
            params = [pair[0] for pair in disc_track_pairs]

        results, code = Database.execute_query(query, params=params, fetchall=True)

        if code == 200:
            # MySQL idx → FAISS idx 변환 (1부터 시작 → 0부터 시작)
            return [result[0] - 1 for result in results]
        else:
            return []
