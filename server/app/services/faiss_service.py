from common.faiss_common import MuseFaiss
from common.oracle_common import OracleDB
from common.mysql_common import Database
from common.redis_common import RedisClient
from daos.playlist_dao import PlaylistDAO
from daos.search_dao import SearchDAO
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import logging

class FaissService:
    @staticmethod
    def search(key: str, query_vector: np.ndarray, k: int = 100) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        try:
            D, I = MuseFaiss.search(key= key, query_vector=query_vector, k=k)
            return D, I
        except Exception as e:
            logging.error(e)
            return None, None
        
    @staticmethod
    def search_with_include(key: str, query_vector: np.ndarray, k: int, playlist_id: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        try:

            # ### DB 에서 불러오는 과정
            # # playlist's all disc trackno           
            # start = time.time()
            # playlist_info = PlaylistDAO.get_playlist_info(playlist_id=playlist_id)
            # logging.info(f'''{key}, search_with_include(PlaylistDAO.get_playlist_info): {time.time()-start} ''')

            # if not playlist_info:
            #     logging.warning(f"No playlist info found for playlist_id: {playlist_id}")
            #     return None, None
            # # disc_track_pairs 생성 [(disccommseq, trackno), ...]
            # disc_track_pairs = [
            #     (song[0], song[1])
            #     for song in playlist_info
            # ]

            # logging.info(f"Total songs in playlist: {len(disc_track_pairs)}")

            # # 배치 크기: 50,000이 최적 (10,000보다 빠름, 100,000은 메모리 부담)
            # batch_size = 50000
            # include_ids = []
            
            # start = time.time()

            # for i in range(0, len(disc_track_pairs), batch_size):
            #     batch = disc_track_pairs[i:i + batch_size]
            #     batch_ids = SearchDAO.get_playlist_idx(key=key, disc_track_pairs=batch)
            #     include_ids.extend(batch_ids)
            #     logging.info(f"Batch {i//batch_size + 1}: Retrieved {len(batch_ids)} idx")
            # logging.info(f'''{key}, search_with_include(SearchDAO.get_playlist_idx): {time.time()-start} ''')

            # logging.info(f"Total include_ids: {len(include_ids)}")


            ### REDIS 에서 불러오는 과정
            include_ids = RedisClient.get_playlist_include_ids(key=key, playlist_id=playlist_id)            

            if not include_ids:
                logging.warning("No include_ids found")
                return None, None

            # FAISS 검색 (include_ids 내에서만)
            D, I = MuseFaiss.search_with_include(key=key, query_vector=query_vector, k=k, include_ids=include_ids)
            
            return D, I
        except Exception as e:
            logging.error(f"Error in search_with_include: {e}")
            return None, None
