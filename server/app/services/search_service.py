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
from rapidfuzz import fuzz
from copy import deepcopy
import re
import time
import json
import math
import io

class SearchService:
    # 스레드 풀 설정 (동시 사용자 대응)
    _executor = ThreadPoolExecutor(max_workers=16)  # CPU 코어 * 2
    _query_executor = ThreadPoolExecutor(max_workers=8)  # CPU 코어 * 2
    _index_mapping = {
        "artist": "muse_artist",
        "album_name": "muse_album_name",
        "title": "muse_title",             
        "vibe": "muse_vibe",
        "lyrics": "muse_lyrics",
        "lyrics_summary": "muse_lyrics_summary"        
    }
    _rank_num = 5
    _k_mapping = {
        "title" : 5000,
        "album_name": 1000,
        "artist": 5000,
        "vibe": 10000,
        "lyrics": 5000,
        "lyrics_summary": 5000
    }
    _batch_size = 1000
    _priority = {        
        "title": 0,
        "album_name": 0,
        "artist": 1,   # title과 동급        
        "vibe": 2,        
        "lyrics_summary": 3,   # 후순위
        "lyrics": 4,   # 후순위        
    }
    
    @staticmethod
    async def _process_batch(key: str, query_text: str, batch_idx_list: list, batch_dist_list: list) -> dict:
        """배치 단위로 곡 정보를 처리하는 비동기 메서드"""
        batched_dict = {
            batch_idx_list[j]: batch_dist_list[j]
            for j in range(len(batch_idx_list))
        }
        
        # 동기 함수를 비동기로 실행
        loop = asyncio.get_event_loop()
        if key == 'album_name':
            # album_info_dict: { '앨범 번호': '인덱스' }            
            album_info_dict = await loop.run_in_executor(
                SearchService._query_executor,
                SearchDAO.get_album_batch_info,
                key,
                batch_idx_list
            )                        
            # song_info_dict: { '인덱스': [{'disccomsseq' : '', 'trackno': ''}] }
            song_info_dict = await loop.run_in_executor(
                SearchService._query_executor,
                SearchDAO.get_song_by_album_info,                
                album_info_dict
            )       

        else:
            # song_info_dict: { '인덱스': {'disccomsseq' : '', 'trackno': ''} }
            song_info_dict = await loop.run_in_executor(
                SearchService._query_executor,
                SearchDAO.get_song_batch_info,
                key,
                batch_idx_list
            )
        
        if not song_info_dict:
            return {}
                
        # disc_track_pairs = [(song_info['disccommseq'], song_info['trackno']) 
        #                   for _, song_info in song_info_dict.items()]
        
        disc_track_pairs = []

        for _, song_info_list in song_info_dict.items():
            for song_info in song_info_list: 
                disc_track_pairs.append((song_info['disccommseq'], song_info['trackno']))

        song_info_idx = {}
        for idx, song_info_list in song_info_dict.items():
            for song_info in song_info_list:
                disc_track_key = f"{song_info['disccommseq']}_{song_info['trackno']}"
                if disc_track_key not in song_info_idx:
                    song_info_idx[disc_track_key] = []
                song_info_idx[disc_track_key].append(idx)
                
        # 병렬로 메타데이터와 mood 정보 가져오기
        song_meta_dict_task = loop.run_in_executor(
            SearchService._query_executor,
            SearchDAO.get_song_batch_meta,
            disc_track_pairs
        )

        mood_value_dict_task = loop.run_in_executor(
            SearchService._query_executor,
            SearchDAO.get_song_mood_value,
            disc_track_pairs
        )

        mood_dict_task = loop.run_in_executor(
            SearchService._query_executor,
            SearchDAO.get_mood_dict
        )

        bpm_value_dict_task = loop.run_in_executor(
            SearchService._query_executor,
            SearchDAO.get_song_bpm_value,
            disc_track_pairs
        )
        
        song_meta_dict, mood_value_dict, mood_dict, bpm_value_dict = await asyncio.gather(
            song_meta_dict_task,
            mood_value_dict_task,
            mood_dict_task,
            bpm_value_dict_task
        )
        
        batch_results = {}
        for song_key, song_meta in song_meta_dict.items():
            idx_list = song_info_idx[song_key]
            song_meta['count'] = 1
            song_meta['dis'] = (
                0.0001 if key == 'artist' and song_meta.get('artist') and 
                query_text.lower().replace(' ','').strip() in 
                song_meta['artist'].lower().replace(' ','').strip()
                else 0.0005 if key == 'title' and song_meta.get('song_name') and 
                query_text.lower().replace(' ','').strip() in 
                song_meta['song_name'].lower().replace(' ','').strip()
                else 0.0001 if key == 'album_name' and song_meta.get('disc_name') and 
                query_text.lower().replace(' ','').strip() in 
                song_meta['disc_name'].lower().replace(' ','').strip()
                else min([float(batched_dict[idx]) for idx in idx_list])
            )
            song_meta['index_name'] = key
            song_meta['main_mood'] = (
                [mood_dict[mood] for mood in json.loads(mood_value_dict[song_key]['mood_list'])]
                if song_key in mood_value_dict else []
            )
            song_meta['bpm'] = bpm_value_dict[song_key] if song_key in bpm_value_dict else 0
            song_meta['energy_level'] = (
                ((mood_value_dict[song_key]['arousal']-1)/16 + 
                 (mood_value_dict[song_key]['valence']-1)/16)*100
                if song_key in mood_value_dict else 50.0
            )
            batch_results[song_key] = song_meta            
        return batch_results

    @staticmethod
    def priority_score(index_name_set):
        """
        세트 내부에서 가장 낮은 우선순위 점수 반환
        (lyrics가 있으면 값이 커져서 후순위로 밀림)
        """
        return max(SearchService._priority.get(v, 0) for v in index_name_set)

    @staticmethod
    def filter_category(region, genre):
        category_dict, genre_set = SearchDAO.get_song_category(), SearchDAO.get_song_genre()
        logging.info(f'''{category_dict}, {genre_set}''')
        if region not in category_dict:
            # 해외 ... 전세계 ...
            if genre in genre_set:
                return True, genre
            return False, None
        
        if genre in category_dict[region]:
            # 국내 전체
            if region == '전체':
                #OST, 어린이, ...
                return True, genre
            # 국내 힙합, 국내 재즈, 해외 재즈, ...
            return True, f'''{region} {genre}'''
        else:     
            if genre in genre_set:
                return True, genre                   
            elif region == '전체':                
                return False, None
            else:
                return True, region
    
        return f'''{region} {genre}'''

        # if genre in category[region]:
        #     return f'''{region} {genre}'''
        # else:
        
        # return 'hello'

    @staticmethod
    async def search_text(text: str, mood: list, timeout: float = 30.0) -> Dict[str, List]:        

        t1 = time.time()

        llm_results = MuseLLM.get_request(text=text, mood=mood)        
        
        if llm_results.get('case') == 14 or not llm_results or len(llm_results) == 1 or all(not llm_results[k] for k in llm_results if k not in {'case', 'llm_model'}):
            llm_results = MuseLLM.get_request(text=text, mood=mood, llm_type='oss')                    
        t2 = time.time()
        logging.info(f'''LLM검색 완료({text}: {t2 - t1}''')        
        
        if 'artist' not in llm_results:
            llm_results['artist'] = []        
        if 'title' not in llm_results:
            llm_results['title'] = []
        if 'album_name' not in llm_results:
            llm_results['album_name'] = []            
        if 'year' not in llm_results:
            llm_results['year'] = []
        if 'popular' not in llm_results:
            llm_results['popular'] = False                
        
        #category 설정
        llm_results['category'] = []

        # llm_results = {
        #     'album_name': ['케이팝데몬헌터스'],
        #     'year': [],
        #     'popular': False
        # }

        try:
            for i in range(len(llm_results['genre'])):
                code, category = SearchService.filter_category(region=llm_results['region'][i], genre=llm_results['genre'][i]) 
                if code:
                    llm_results['category'].append(category)
        except Exception as e:
            logging.error(e)                

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

        merged_list.sort(key=lambda x: x["dis"], reverse=False)     
        # merged_list.sort(key=lambda x: (SearchService.priority_score(x["index_name_set"]), x["dis"]), reverse=False)   
        
        total_dict = {}

        for song_dict in merged_list:
            if len(total_dict) >= 500:
                break
            song_key_artist = song_dict['artist'].lower().replace(' ','').strip() if song_dict['artist'] else ''
            song_key_title = song_dict['song_name'].lower().replace(' ','').strip() if song_dict['song_name'] else ''
            song_key = f'''{song_key_artist}_{song_key_title} '''
            if song_key not in total_dict:
                total_dict[song_key] = deepcopy(song_dict)
                continue
            if total_dict[song_key]['hit_year']:
               continue
            elif song_dict['hit_year']:
                total_dict[song_key] = deepcopy(song_dict)

        total_list = [ v for _, v in total_dict.items() ]           

        total_results = {
            'year_list': llm_results['year'] if 'year' in llm_results else [],
            'popular': llm_results['popular'][0] if 'popular' in llm_results and llm_results['popular'] else False,
            'search_keyword': llm_results,
            'results': total_list
        }        
        
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
            if key not in ['artist', 'title', 'lyrics', 'lyrics_summary', 'vibe', 'album_name']:
            # if key not in ['artist', 'title', 'lyrics', 'lyrics_summary', 'vibe']:
                return (key, {})
        
            
            D, I = FaissService.search(key=key, query_vector=query_vector, k=SearchService._k_mapping[key])                                        
            logging.info(f''' FAISS SEARCH: {key}, {query_text} {D} {I}''')
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
   
            # 병렬 처리를 위한 태스크 생성
            tasks = []
            for batch_idx_list, batch_dist_list in zip(batched_I, batched_D):
                tasks.append(SearchService._process_batch(key, query_text, batch_idx_list, batch_dist_list))
            
            # 이벤트 루프에서 비동기 함수 실행
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # 모든 배치를 병렬로 처리하고 결과 병합
            batch_results = loop.run_until_complete(asyncio.gather(*tasks))
            results = {}
            for batch_result in batch_results:
                results.update(batch_result)
            
            t6 = time.time()   
            logging.info(f'''\tFAISS_{key}_{query_text} 검색 완료: {t6-t2}''')
            return (key, results)
            
        except Exception as e:
            logging.error(f"Error in FAISS search for {key}: {e}")
            return (key, {})
        
    @staticmethod
    def _normalize_for_dedup(text):
        """중복 제거를 위한 텍스트 정규화"""        
        if not text:
            return ""
        # 파일 확장자 제거
        text = re.sub(r'\.(mp3|wav|flac|m4a)$', '', text, flags=re.IGNORECASE)
        # 괄호 안 내용 제거 (리메이크, 버전 정보 등)
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        # * 뒤에 오는 remix, ver, version 등의 문자 제거
        text = re.sub(r'\*.*$', '', text, flags=re.IGNORECASE)
        # 특수문자 제거, 소문자 변환, 공백 정규화
        text = re.sub(r'[^\w\s가-힣]', '', text)
        text = ' '.join(text.lower().split())
        return text
    
    @staticmethod
    def _is_duplicate_song(artist1, title1, artist2, title2, threshold=0.85):
        """두 곡이 중복인지 판단 (정규화 + 유사도 체크)"""
        # 먼저 정규화된 문자열로 정확한 매칭 체크
        norm_artist1 = SearchService._normalize_for_dedup(artist1)
        norm_title1 = SearchService._normalize_for_dedup(title1)
        norm_artist2 = SearchService._normalize_for_dedup(artist2)
        norm_title2 = SearchService._normalize_for_dedup(title2)
        
        # 정규화된 결과가 완전히 같으면 중복
        if norm_artist1 == norm_artist2 and norm_title1 == norm_title2:
            return True
        
        # 선택적: rapidfuzz를 사용한 유사도 체크 (설치 필요시)
        try:            
            # artist와 title 조합으로 비교
            combined1 = f"{norm_artist1} {norm_title1}"
            combined2 = f"{norm_artist2} {norm_title2}"
            similarity = fuzz.ratio(combined1, combined2) / 100.0
            return similarity >= threshold
        except ImportError:
            # rapidfuzz가 없으면 정규화 매칭만 사용
            return False

    @staticmethod
    async def search_similar_song(key, disccommseq, trackno):
        try:
            results = {}
            # 타겟 곡의 메타 정보 가져오기
            start=time.time()        
            target_meta = SearchDAO.get_song_meta(disccommseq=disccommseq, trackno=trackno)          
            target_artist = target_meta.get('artist', '')
            target_title = target_meta.get('song_name', '')
            
            #SearchDAO    에서 disc_comm_seq, track_no 관련된 곡 시퀀스 정보 가져오기
            if key == 'vibe':
                embedding_results = SearchDAO.get_song_clap_embedding(key=key, disccommseq=disccommseq, trackno=trackno)
            elif key == 'lyrics_summary':
                embedding_results = SearchDAO.get_song_clap_lyric_summary(key=key, disccommseq=disccommseq, trackno=trackno)                                
                if not embedding_results:
                    key = 'title'
                    embedding_results=SearchDAO.get_song_bgem3_song_name(key=key, disccommseq=disccommseq, trackno=trackno)
                    
            else:
                embedding_results = []
            
            embedding_results = [ np.atleast_2d(np.load(io.BytesIO(embedding_result), allow_pickle=True))[0] for embedding_result in embedding_results]
            batched_I = []
            
            for embedding_result in embedding_results:
                D, I = FaissService.search(key=key, query_vector=embedding_result, k=100)                                                    
                batched_I.append([int(idx)+1 for idx in I[0]])
            
            for _, batch_idx_list in enumerate(batched_I):
                song_info_dict = SearchDAO.get_song_batch_info(key=key, idx_list=batch_idx_list)
                if song_info_dict:
                    disc_track_pairs = []
                    for _, song_info_list in song_info_dict.items():
                        for song_info in song_info_list:
                            disc_track_pairs.append((song_info['disccommseq'], song_info['trackno']))
                    # disc_track_pairs = [(song_info['disccommseq'], song_info['trackno']) for _, song_info in song_info_dict.items()]         
                    song_info_idx = {}           
                    for idx, song_info_list in song_info_dict.items():
                        for song_info in song_info_list:
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
            
            # 정확히 같은 disc_id, track_id 제거
            if f'''{disccommseq}_{trackno}''' in results:
                del results[f'''{disccommseq}_{trackno}''']
                
            sorted_results = sorted(results.items(), key=lambda x: x[1]['count'], reverse=True)
            
            # 중복 제거 로직 추가
            final_tracks = []
            seen_songs = []  # (artist, title) 튜플 저장
            
            for song_key, song_data in sorted_results:
                if len(final_tracks) >= 5:
                    break
                    
                meta = song_data['meta']
                current_artist = meta['artist']
                current_title = meta['song_name']
                
                # 타겟 곡과 중복 체크 (타겟 곡의 다른 버전들 제외)
                if SearchService._is_duplicate_song(current_artist, current_title, 
                                                   target_artist, target_title):
                    continue
                
                # 이미 추가된 곡들과 중복 체크
                is_duplicate = False
                for seen_artist, seen_title in seen_songs:
                    if SearchService._is_duplicate_song(current_artist, current_title, 
                                                       seen_artist, seen_title):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    final_tracks.append({
                        'disc_id': meta['disc_comm_seq'],
                        'track_id': meta['track_no'],
                        'title': current_title,
                        'artist': current_artist,
                        'jpg_file_name': meta['jpg_file_name'],
                        'mp3_path_flag': meta['mp3_path_flag']
                    })
                    seen_songs.append((current_artist, current_title))
            
            return {'similar_tracks': final_tracks}
        except Exception as e:
            logging.error(e)
            return {'similar_tracks': []}
        
    @staticmethod
    async def search_analyze_result(text, llm_result, disccommseq, trackno):
        try:
            song_info = SearchDAO.get_song_meta(disccommseq=disccommseq, trackno=trackno)        
            analyze_result = MuseLLM.get_reason(text=text, llm_result=llm_result, song_info=song_info)            

            if analyze_result:
                analyze_result = json.loads(analyze_result)
                logging.info(analyze_result)
                if 'response' in analyze_result:
                    return {'result': {'analyze': analyze_result['response']}}
                elif 'description' in analyze_result:
                    return {'result': {'analyze': analyze_result['description']}}
            else:
                return {'result': {'analyze': []}}
            
        except Exception as e:
            return {'result': {'analyze': []}}
            