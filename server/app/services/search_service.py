import asyncio
from typing import Dict, List, Any, Optional
import numpy as np
import logging
from services.embedding_service import EmbeddingService
from concurrent.futures import ThreadPoolExecutor
from common.llm_common import MuseLLM
from common.faiss_common import MuseFaiss
from services.faiss_service import FaissService
from daos.search_dao import SearchDAO
import time
import json

class SearchService:
    # 스레드 풀 설정 (동시 사용자 대응)
    _executor = ThreadPoolExecutor(max_workers=16)  # CPU 코어 * 2
    _index_mapping = {
            "artist": "muse_artist",
            "title": "muse_title",             
            "vibe": "muse_vibe"
        }

    @staticmethod
    async def search_text(text: str, timeout: float = 20.0) -> Dict[str, List]:
        
        llm_results = MuseLLM.get_request(text=text)
        print(llm_results)
        # llm_results = {"artist":"", "title":"", "genre": "", "mood":[], "vibe":[], "year":"2024", "popular":True}        
        if not llm_results:
            return {}                
        
        search_coroutines = []
        task_keys = []
        
        for key, values in json.loads(llm_results).items():
            # llm_results = {"artist":"", "title":"", "genre": "", "mood":[], "year":"2024", "popular":True}     
               
            if values and key in SearchService._index_mapping:            
                for value in values:
                    job = SearchService._search_single_index(key=key, query_text=value, index_file_name=SearchService._index_mapping[key])
                    search_coroutines.append(job)
                    task_keys.append(key)        
        
        try:
            results_list = await asyncio.wait_for(
                asyncio.gather(*search_coroutines, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logging.error(f"Search operation timed out after {timeout}s")
            return {key: [] for key in task_keys}
        
        return results_list
        # 결과 처리
        results = {}
        for i, result in enumerate(results_list):
            key = task_keys[i]
            
            if isinstance(result, asyncio.TimeoutError):
                logging.warning(f"Search timeout for {key}")
                results[key] = []
            elif isinstance(result, Exception):
                logging.error(f"Search error for {key}: {result}")
                results[key] = []
            else:
                results[key] = result
                logging.info(f"Search completed for {key}: {len(result)} results")
        
        return results
    
    @staticmethod
    async def _search_single_index(key: str, query_text: str, index_file_name: str, timeout: float = 5.0) -> List:
        try:
            # 공유 스레드 풀 사용 (교착상태 방지)
            loop = asyncio.get_event_loop()
            
            # 개별 검색에 타임아웃 적용
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    SearchService._executor,  # 명시적 executor 사용
                    SearchService._faiss_search,
                    key, query_text, index_file_name
                ),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logging.warning(f"Individual search timeout for {key} after {timeout}s")
            return []
        except Exception as e:
            logging.error(f"Error in _search_single_index for {key}: {e}")
            return []
    
    @staticmethod
    def _faiss_search(key: str, query_text: Any, index_file_name: str) -> List:
        #artist, title, vibe
        try:                        
            query_vector = EmbeddingService.get_vector(key=key, text=query_text)  
            
            D, I = FaissService.search(key=key, query_vector=query_vector, k=100)            
            print('------', key, query_text, I[0])          
            
            if D is None or I is None:
                return []
            
            # 검색 결과 반환
            results = []

            for i, (idx, dist) in enumerate(zip(I[0], D[0])):
                if idx != -1:  # FAISS에서 -1은 결과 없음을 의미
                    song_info = SearchDAO.get_song_info(key=key, idx=idx)                    
                    if song_info:
                        disccommseq, trackno = song_info['disccommseq'], song_info['trackno']
                        song_meta = SearchDAO.get_song_meta(disccommseq=disccommseq, trackno=trackno)                        
                        results.append(song_meta)
            
            return results
            
        except Exception as e:
            print(f"Error in FAISS search for {key}: {e}")
            return []