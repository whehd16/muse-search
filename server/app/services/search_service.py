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
from collections import defaultdict
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
    _rank_num = 5
    _k_mapping = {
        "title" : 50000,
        "artist": 2000,
        "vibe": 10000
    }
    _batch_size = 1000

    @staticmethod
    async def search_text(text: str, timeout: float = 30.0) -> Dict[str, List]:
        
        llm_results = MuseLLM.get_request(text=text)
        llm_results = json.loads(llm_results)
        print(llm_results)
        # llm_results = {"artist":"", "title":"", "genre": "", "mood":[], "vibe":[], "year":"2024", "popular":True}        
        if not llm_results:
            return {
                'year_list': [],
                'popular': False,
                'results': []
            }                
        
        search_coroutines = []
        task_keys = []
        
        for key, values in llm_results.items():
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
        
        # print(results_list)
        # for d in results_list:
        #     for k, v in d.items():
        #         logging.info(f'''{k}, {v}''')

        merged = defaultdict(lambda: None)

        for group in results_list:
            for key, song_info in group.items():
                if merged[key] is None:
                    # 처음 등장하는 곡이면 복사
                    merged[key] = song_info.copy()
                    merged[key]["index_name_set"] = set([merged[key]["index_name"]])
                else:                                        
                    merged[key]["count"] += 1
                    if song_info.get("index_name") in merged[key]["index_name_set"]:
                        merged[key]["dis"] /= 2
                    else:
                        merged[key]["dis"] *= song_info.get("dis", 0.0)
                        merged[key]["index_name_set"].add(song_info.get("index_name"))

        # dict → list 변환
        merged_list = list(merged.values())

        # count 기준으로 내림차순 정렬
        merged_list.sort(key=lambda x: x["dis"], reverse=False)

        # for item in merged_list[:100]:
        #     # logging.info(f'''{item["dis"]}, {item["count"]}, {item["artist"]}, {item["song_name"]}, {item['disc_comm_seq']} / {item['track_no']})''')
        #     print(f'''{item["dis"]}, {item["count"]}, {item["artist"]}, {item["song_name"]}, {item['disc_comm_seq']} / {item['track_no']})''')
        total_results = {
            'year_list': llm_results['year'],
            'popular': llm_results['popular'][0] if llm_results['popular'] else False,
            'results': merged_list
        }        
        
        # select_reasons = json.loads(MuseLLM.get_reason(text=text, total_results=total_results, rank=SearchService._rank_num))        
        # select_reasons = select_reasons['response'] if 'response' in select_reasons else []
        
        # for rank in range(SearchService._rank_num):
        #     total_results['results'][rank]['select_reason'] = select_reasons[rank]

        return total_results
    
    @staticmethod
    async def _search_single_index(key: str, query_text: str, index_file_name: str, timeout: float = 20.0) -> List:
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
    def _faiss_search(key: str, query_text: Any, index_file_name: str) -> Dict:
        #artist, title, vibe
        try:                        
            query_vector = EmbeddingService.get_vector(key=key, text=query_text.lower().replace(' ',''))              
            if key not in ['artist', 'title']:
                return {}

            D, I = FaissService.search(key=key, query_vector=query_vector, k=SearchService._k_mapping[key])                            
            
            if D is None or I is None:
                return []
            
            # 검색 결과 반환
            results = {}
            
            # ##
            # 묶음(배치) 검색
            batched_D = []
            batched_I = []
            
            for i in range(0, len(I[0]), SearchService._batch_size):
                batched_I.append([ int(I[0][idx])+1 for idx in range(i, min(len(I[0]), i+SearchService._batch_size))])                                
                batched_D.append([ float(D[0][idx]) for idx in range(i, min(len(I[0]), i+SearchService._batch_size))])                            
            
            for i, (batch_idx_list, batch_dist_list) in enumerate(zip(batched_I, batched_D)):                   
                batched_dict = { # idx: dis
                    batch_idx_list[j]: batch_dist_list[j]
                    for j in range(len(batch_idx_list))
                }                
    
                song_info_dict = SearchDAO.get_song_batch_info(key=key, idx_list=batch_idx_list)
                # >> song_info_dict=:{ idx:{'disccommseq': "", 'trackno':""}}

                if song_info_dict:
                    disc_track_pairs = [(song_info['disccommseq'], song_info['trackno']) for _, song_info in song_info_dict.items()]
                    song_info_idx = { 
                        f'''{song_info['disccommseq']}_{song_info['trackno']}''': idx 
                        for idx, song_info in song_info_dict.items()
                    }
                    
                    song_meta_dict = SearchDAO.get_song_batch_meta(disc_track_pairs=disc_track_pairs)                    
                    # print(f'''FIRST {query_text}, {song_meta_dict}''')
                    for song_key, song_meta in song_meta_dict.items():                        
                        song_meta['count'] = 1
                        idx = song_info_idx[song_key]                                                
                        song_meta['dis'] = float(batched_dict[idx])
                        song_meta['index_name'] = key
                        results[f'''{song_key}'''] = song_meta                
                
                # if song_info_dict:
                #     for idx, song_info in song_info_dict.items():
                #         disccommseq, trackno = song_info['disccommseq'], song_info['trackno']
                #         song_meta = SearchDAO.get_song_meta(disccommseq=disccommseq, trackno=trackno)                        
                #         print(f'''SECOND {query_text}, {idx}, {song_meta}''')
                #         song_meta['count'] = 1   
                #         song_meta['dis'] = float(batched_dict[idx])
                #         song_meta['index_name'] = key
                #         results[f'''{song_meta['disc_comm_seq']}_{song_meta['track_no']}'''] = song_meta

            # ##

            # # 개별검색
            # for i, (idx, dist) in enumerate(zip(I[0], D[0])):
            #     if idx != -1:  # FAISS에서 -1은 결과 없음을 의미
            #         song_info = SearchDAO.get_song_info(key=key, idx=idx)                    
            #         if song_info:
            #             disccommseq, trackno = song_info['disccommseq'], song_info['trackno']
            #             song_meta = SearchDAO.get_song_meta(disccommseq=disccommseq, trackno=trackno)
            #             song_meta['count'] = 1   
            #             song_meta['dis'] = float(dist)
            #             song_meta['index_name'] = key
            #             results[f'''{song_meta['disc_comm_seq']}_{song_meta['track_no']}'''] = song_meta
            
            return results
            
        except Exception as e:
            print(f"Error in FAISS search for {key}: {e}")
            return []