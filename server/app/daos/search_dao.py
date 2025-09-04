from common.mysql_common import Database
from common.oracle_common import OracleDB
from typing import List, Dict


class SearchDAO:
    _table_mapping ={
        'artist': 'tb_embedding_bgem3_artist_h',
        'title': 'tb_embedding_bgem3_song_name_h',
        'vibe' : 'tb_embedding_clap_h',
        'lyrics': 'tb_embedding_bgem3_lyrics_slide_h',
        'lyrics_summary': 'tb_embedding_clap_lyrics_summary_h'
    }
    
    @staticmethod
    def get_song_batch_info(key: str, idx_list: List):
        batch_info = {}        
        results, code = Database.execute_query(f"""
            SELECT idx, disccommseq, trackno
            FROM {SearchDAO._table_mapping[key]}
            WHERE idx in ({','.join(list(map(str, idx_list)))})
        """, fetchall=True)
        if code == 200:
            for result in results:
                batch_info[result[0]] = {
                    'disccommseq': result[1],
                    'trackno': result[2]
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
    def get_song_batch_meta(disc_track_pairs: List[tuple]):

        if not disc_track_pairs:
            return {}

        conditions = []
        
        for disccommseq, trackno in disc_track_pairs:
            conditions.append(f"(A.DISC_COMM_SEQ={disccommseq} AND A.TRACK_NO='{trackno}')")
        
        where_clause =" OR ".join(conditions)
        results = OracleDB.execute_query(f"""
            SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, 
            B.DISC_NAME, A.DISC_COMM_SEQ, A.TRACK_NO, MASTERING_YEAR, HIT_YEAR, B.DISC_GENRE_TXT
            FROM MIBIS.MI_SONG_INFO A 
            JOIN MIBIS.MI_DISC_INFO B 
            ON A.DISC_COMM_SEQ = B.DISC_COMM_SEQ 
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
            SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, B.DISC_NAME, A.DISC_COMM_SEQ, A.TRACK_NO, MASTERING_YEAR, HIT_YEAR, B.DISC_GENRE_TXT
            FROM MIBIS.MI_SONG_INFO A 
            JOIN MIBIS.MI_DISC_INFO B 
            ON A.DISC_COMM_SEQ = B.DISC_COMM_SEQ 
            WHERE A.DISC_COMM_SEQ={disccommseq} AND A.TRACK_NO='{trackno}'
        """)
        if result:
            try:
                result[0]['track_no'] = result[0]['track_no'].strip()
            except:
                pass
            return result[0]