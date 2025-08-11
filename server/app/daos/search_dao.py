from common.mysql_common import Database
from common.oracle_common import OracleDB
from typing import List, Dict


class SearchDAO:
    _table_mapping ={
        'artist': 'tb_embedding_bgem3_artist_h',
        'title': 'tb_embedding_bgem3_song_name_h',
        'vibe' : 'tb_embedding_clap_h'
    }
    
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
    def get_song_meta(disccommseq: int, trackno: str) -> Dict:
        result = OracleDB.execute_query(f"""
            SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, B.DISC_NAME, A.DISC_COMM_SEQ, A.TRACK_NO
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