import asyncio
from typing import Dict, List, Any, Optional, Tuple
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
import math
import io

class SearchService:
    # 스레드 풀 설정 (동시 사용자 대응)
    _executor = ThreadPoolExecutor(max_workers=16)  # CPU 코어 * 2
    _index_mapping = {
        "artist": "muse_artist",
        "title": "muse_title",             
        "vibe": "muse_vibe",
        "lyrics": "muse_lyrics",
        "lyrics_summary": "muse_lyrics_summary"
    }
    _rank_num = 5
    _k_mapping = {
        "title" : 5000,
        "artist": 5000,
        "vibe": 10000,
        "lyrics": 5000,
        "lyrics_summary": 5000

    }
    _batch_size = 1000
    _priority = {
        "vibe": 0,        
        "title": 1,
        "artist": 2,   # title과 동급        
        "lyrics_summary": 3,   # 후순위
        "lyrics": 4,   # 후순위
        
    }
    
    @staticmethod
    def priority_score(index_name_set):
        """
        세트 내부에서 가장 낮은 우선순위 점수 반환
        (lyrics가 있으면 값이 커져서 후순위로 밀림)
        """
        return max(SearchService._priority.get(v, 0) for v in index_name_set)


    @staticmethod
    async def search_text(text: str, mood: list, timeout: float = 30.0) -> Dict[str, List]:        

        t1 = time.time()


        llm_results = MuseLLM.get_request(text=text, mood=mood)        
        if llm_results.get('case') == 12 or not llm_results or len(llm_results) == 1 or all(not llm_results[k] for k in llm_results if k not in {'case', 'llm_model'}):
            llm_results = MuseLLM.get_request(text=text, mood=mood, llm_type='oss')            

        t2 = time.time()
        logging.info(f'''LLM검색 완료({text}: {t2 - t1}''')

        if 'artist' not in llm_results:
            llm_results['artist'] = []
        if 'title' not in llm_results:
            llm_results['title'] = []
        if 'year' not in llm_results:
            llm_results['year'] = []
        if 'popular' not in llm_results:
            llm_results['popular'] = False                

        logging.info(llm_results)
        search_coroutines = []
        task_keys = []
        for key, values in llm_results.items():
            # llm_results = {"artist":""", "title":"", "genre": "", "mood":[], "year":"2024", "popular":True}     
               
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
        
        # logging.info(results_list)
        # for d in results_list:
        #     for k, v in d.items():
        #         logging.info(f'''{k}, {v}''')
        
        t3 = time.time()
        logging.info(f'''FAISS 검색 완료({text}): {t3 - t2}''')

        merged = defaultdict(lambda: None)

        for (key, group) in results_list:     
            
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

        t4 = time.time()
        logging.info(f'''결과 병합 완료({text}: {t4 - t3}''')        
        
        # dict → list 변환
        merged_list = list(merged.values())
        # logging.info(merged_list)
        # count 기준으로 내림차순 정렬        
        merged_list.sort(key=lambda x: x["dis"], reverse=False)        
        # merged_list.sort(key=lambda x: ( -len(x["index_name_set"]), SearchService.priority_score(x["index_name_set"]), x["dis"]))
        
        # merged_list.sort(key=lambda x: len(x[""], reverse=False)

        # for item in merged_list[:100]:
        #     # logging.info(f'''{item["dis"]}, {item["count"]}, {item["artist"]}, {item["song_name"]}, {item['disc_comm_seq']} / {item['track_no']})''')
        #     print(f'''{item["dis"]}, {item["count"]}, {item["artist"]}, {item["song_name"]}, {item['disc_comm_seq']} / {item['track_no']})''')
        total_results = {
            'year_list': llm_results['year'],
            'popular': llm_results['popular'][0] if llm_results['popular'] else False,
            'search_keyword': llm_results,
            'results': merged_list            
        }        
        
        # try:
        #     select_reasons = json.loads(MuseLLM.get_reason(text=text, total_results=total_results, rank=SearchService._rank_num))           
        #     select_reasons = select_reasons['response'] if 'response' in select_reasons else []
            
        #     for rank in range(SearchService._rank_num):
        #         total_results['results'][rank]['select_reason'] = select_reasons[rank]
        # except Exception as e:
        #     print(e)
        
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
    def _faiss_search(key: str, query_text: Any, index_file_name: str) -> Tuple:
        #artist, title, vibe
        try:                
            t1 = time.time()
            query_vector = EmbeddingService.get_vector(key=key, text=query_text.lower().replace(' ',''))                       
            if key not in ['artist', 'title', 'lyrics', 'lyrics_summary', 'vibe']:
                return (key, {})
            D, I = FaissService.search(key=key, query_vector=query_vector, k=SearchService._k_mapping[key])                                        
            
            if D is None or I is None:
                return (key, {})                

            # 검색 결과 반환
            results = {}
            
            # ##
            # 묶음(배치) 검색
            batched_D = []
            batched_I = []

            for i in range(0, len(I[0]), SearchService._batch_size):
                batched_I.append([ int(I[0][idx])+1 for idx in range(i, min(len(I[0]), i+SearchService._batch_size))])                                
                batched_D.append([ float(D[0][idx]) for idx in range(i, min(len(I[0]), i+SearchService._batch_size))])                            
            
            t2 = time.time()   
            logging.info(f'''\t\tFAISS_{key}_{query_text} D, I 검색 완료: {t2-t1}''')
            for i, (batch_idx_list, batch_dist_list) in enumerate(zip(batched_I, batched_D)):                   
                batched_dict = { # idx: dis
                    batch_idx_list[j]: batch_dist_list[j]
                    for j in range(len(batch_idx_list))
                }                
                song_info_dict = SearchDAO.get_song_batch_info(key=key, idx_list=batch_idx_list)
                # >> song_info_dict=:{ idx:{'disccommseq': "", 'trackno':""}}
                if song_info_dict:
                    disc_track_pairs = [(song_info['disccommseq'], song_info['trackno']) for _, song_info in song_info_dict.items()]         
                    song_info_idx = {}           
                    for idx, song_info in song_info_dict.items():
                        if f'''{song_info['disccommseq']}_{song_info['trackno']}''' not in song_info_idx:
                            song_info_idx[f'''{song_info['disccommseq']}_{song_info['trackno']}'''] = []
                        song_info_idx[f'''{song_info['disccommseq']}_{song_info['trackno']}'''].append(idx)     
                    t4_1 = time.time()
                    song_meta_dict = SearchDAO.get_song_batch_meta(disc_track_pairs=disc_track_pairs)
                    t4_2 = time.time()
                    logging.info(f'''\t\t\t get_song_batch_meta: {t4_2-t4_1}''')
                    mood_value_dict = SearchDAO.get_song_mood_value(disc_track_pairs=disc_track_pairs)                           
                    mood_dict = SearchDAO.get_mood_dict()
                    
                    t4_3 = time.time()
                    logging.info(f'''\t\t\t get_song_mood_value({len(disc_track_pairs)}): {t4_3-t4_2}''')
                    
                    for song_key, song_meta in song_meta_dict.items():                            
                        idx_list = song_info_idx[song_key]                                                                                                                 
                        song_meta['count'] = 1                    
                        song_meta['dis'] =  0.0001 if key == 'artist' and song_meta['artist'] and query_text.lower().replace(' ','').strip() in song_meta['artist'].lower().replace(' ','').strip() else 0.0005 if key == 'title' and song_meta['song_name'] and query_text.lower().replace(' ','').strip() in song_meta['song_name'].lower().replace(' ','').strip() else min([float(batched_dict[idx]) for idx in idx_list])                                                
                        song_meta['index_name'] = key
                        song_meta['main_mood'] = [ mood_dict[mood] for mood in json.loads(mood_value_dict[song_key]['mood_list']) ] if song_key in mood_value_dict else []
                        song_meta['energy_level'] = ((mood_value_dict[song_key]['arousal']-1)/16 + (mood_value_dict[song_key]['valence']-1)/16)*100 if song_key in mood_value_dict else 50.0
                        results[f'''{song_key}'''] = song_meta      
                    t4_4 = time.time()
                    logging.info(f'''\t\t\t done: {t4_4-t4_3}''')                
   
            t6 = time.time()   
            logging.info(f'''\tFAISS_{key}_{query_text} 검색 완료: {t6-t2}''')
            return (key, results)
            
        except Exception as e:
            print(f"Error in FAISS search for {key}: {e}")
            return (key, {})
        
    @staticmethod
    async def search_similar_song(key, disccommseq, trackno):
        try:
            results = {}
            #SearchDAO    에서 disc_comm_seq, track_no 관련된 곡 시퀀스 정보 가져오기
            embedding_results = SearchDAO.get_song_clap_embedding(key=key, disccommseq=disccommseq, trackno=trackno)
            embedding_results = [ np.atleast_2d(np.load(io.BytesIO(embedding_result), allow_pickle=True))[0] for embedding_result in embedding_results]
            batched_I = []
            
            for embedding_result in embedding_results:
                D, I = FaissService.search(key=key, query_vector=embedding_result, k=100)                                                    
                batched_I.append([int(idx)+1 for idx in I[0]])
            
            for _, batch_idx_list in enumerate(batched_I):
                song_info_dict = SearchDAO.get_song_batch_info(key=key, idx_list=batch_idx_list)
                if song_info_dict:
                    disc_track_pairs = [(song_info['disccommseq'], song_info['trackno']) for _, song_info in song_info_dict.items()]         
                    song_info_idx = {}           
                    for idx, song_info in song_info_dict.items():
                        if f'''{song_info['disccommseq']}_{song_info['trackno']}''' not in song_info_idx:
                            song_info_idx[f'''{song_info['disccommseq']}_{song_info['trackno']}'''] = []
                        song_info_idx[f'''{song_info['disccommseq']}_{song_info['trackno']}'''].append(idx)     
                
                    song_meta_dict = SearchDAO.get_song_batch_meta(disc_track_pairs=disc_track_pairs)                                        
                    
                    for song_key, song_meta in song_meta_dict.items():      
                        
                        if song_key not in results:
                            results[song_key] = {
                                'count': 0,
                                'meta': song_meta
                            }             
                        results[song_key]['count'] += 1         
            if f'''{disccommseq}_{trackno}''' in results:
                del results[f'''{disccommseq}_{trackno}''']
                
            sorted_results = sorted(results.items(), key=lambda x: x[1]['count'], reverse=True)
            similar_tracks = [ 
                { 
                    'disc_id': sorted_results[i][1]['meta']['disc_comm_seq'],
                    'track_id' : sorted_results[i][1]['meta']['track_no'],
                    'title': sorted_results[i][1]['meta']['song_name'],
                    'artist' : sorted_results[i][1]['meta']['artist'],
                    'jpg_file_name': sorted_results[i][1]['meta']['jpg_file_name'] 
                } for i in range(min(5, len(sorted_results)))
            ]  

            return {'similar_tracks': similar_tracks}
        except Exception as e:
            logging.error(e)
            return {'similar_tracks': []}