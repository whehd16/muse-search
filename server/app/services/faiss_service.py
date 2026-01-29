from common.faiss_common import MuseFaiss
from common.oracle_common import OracleDB
from common.mysql_common import Database
from common.redis_common import RedisClient
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
