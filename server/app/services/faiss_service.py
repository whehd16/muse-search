from common.faiss_common import MuseFaiss
from common.oracle_common import OracleDB
from common.mysql_common import Database
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
