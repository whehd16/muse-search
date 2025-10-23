import faiss
import numpy as np
import logging
from typing import Dict, Tuple, Optional, List
from config import INDEX_PATH

class MuseFaiss:
    # 인덱스를 클래스 변수로 미리 로드
    indices: Dict[str, faiss.Index] = {}
    
    # 초기화 시 모든 인덱스 로드
    try:
        indices['artist'] = faiss.read_index(f'{INDEX_PATH}/muse_artist.index')
        logging.info(f"Loaded artist index: {indices['artist'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load artist index, trying backup: {e}")
        try:
            indices['artist'] = faiss.read_index(f'{INDEX_PATH}/muse_artist_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load artist backup index: {e2}")
    
    try:
        indices['title'] = faiss.read_index(f'{INDEX_PATH}/muse_title.index')
        logging.info(f"Loaded title index: {indices['title'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load title index, trying backup: {e}")
        try:
            indices['title'] = faiss.read_index(f'{INDEX_PATH}/muse_title_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load title backup index: {e2}")
    
    try:
        indices['vibe'] = faiss.read_index(f'{INDEX_PATH}/muse_vibe.index')
        logging.info(f"Loaded vibe index: {indices['vibe'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load vibe index, trying backup: {e}")
        try:
            indices['vibe'] = faiss.read_index(f'{INDEX_PATH}/muse_vibe_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load vibe backup index: {e2}")

    try:
        indices['lyrics'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics.index')
        logging.info(f"Loaded lyrics index: {indices['lyrics'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load lyrics index, trying backup: {e}")
        try:
            indices['lyrics'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load lyrics backup index: {e2}")

    try:
        indices['lyrics_3'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_3.index')
        logging.info(f"Loaded lyrics_3 index: {indices['lyrics_3'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load lyrics_3 index, trying backup: {e}")
        try:
            indices['lyrics_3'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_3_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load lyrics_3 backup index: {e2}")

    try:
        indices['lyrics_summary'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_summary.index')
        logging.info(f"Loaded lyrics_summary index: {indices['lyrics_summary'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load lyrics_summary index, trying backup: {e}")
        try:
            indices['lyrics_summary'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_summary_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load lyrics_summary backup index: {e2}")

    try:
        indices['album_name'] = faiss.read_index(f'{INDEX_PATH}/muse_album_name.index')
        logging.info(f"Loaded album name index: {indices['album_name'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load album name index, trying backup: {e}")
        try:
            indices['album_name'] = faiss.read_index(f'{INDEX_PATH}/muse_album_name_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load album name backup index: {e2}")

    @staticmethod
    def search(key: str, query_vector: np.ndarray, k: int = 100) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """특정 인덱스에서 검색 수행"""
        if key not in MuseFaiss.indices:
            logging.error(f"Index type '{key}' not found. Available: {list(MuseFaiss.indices.keys())}")
            return None, None
        
        try:
            index = MuseFaiss.indices[key]
            # 쿼리 벡터가 1차원이면 2차원으로 변환
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            
            D, I = index.search(query_vector.astype('float32'), k)                        
            if key in ['artist', 'lyrics', 'title']:
                # logging.info(f'''threshold 적용 {key}''')
                threshold = 0.9  # 예시 (L2 distance일 경우)

                # L2 기반일 때 (작을수록 유사)
                mask = D > threshold
                D[mask] = np.inf   # 무효값으로 처리
                I[mask] = -1       # 유효하지 않은 인덱스는 -1로

            return D, I
        except Exception as e:
            logging.error(f"Search error in {key} index: {e}")
            return None, None

    @staticmethod
    def search_with_include(key: str, query_vector: np.ndarray, k: int, include_ids: List[int]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        include_ids 내에서만 검색 (IDSelectorBitmap 사용)

        Args:
            key: 인덱스 타입 (artist, title, vibe, lyrics, etc.)
            query_vector: 쿼리 벡터 (1D 또는 2D)
            k: 반환할 결과 개수
            include_ids: 검색 대상 인덱스 리스트 (예: [10, 100, 1000, ...])

        Returns:
            D: 거리 배열 (shape: (1, k))
            I: 인덱스 배열 (shape: (1, k))

        Note:
            - include_ids가 k보다 적으면 최대 len(include_ids)개만 반환됨
            - IVFPQ, IVF 계열 인덱스에서만 작동 (Flat 인덱스는 fallback 사용)
            - 4000만개 인덱스에서 10만개 include_ids 검색 시 비트맵 메모리: ~5MB
        """
        if key not in MuseFaiss.indices:
            logging.error(f"Index type '{key}' not found. Available: {list(MuseFaiss.indices.keys())}")
            return None, None

        if not include_ids or len(include_ids) == 0:
            logging.error("include_ids is empty")
            return None, None

        try:
            index = MuseFaiss.indices[key]
            n_total = index.ntotal

            # 쿼리 벡터가 1차원이면 2차원으로 변환
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)

            # include_ids 범위 검증 및 필터링
            valid_include_ids = [id for id in include_ids if 0 <= id < n_total]
            if len(valid_include_ids) < len(include_ids):
                logging.warning(f"Filtered out {len(include_ids) - len(valid_include_ids)} invalid IDs (out of range 0-{n_total})")

            if len(valid_include_ids) == 0:
                logging.error("No valid include_ids after range check")
                return None, None

            # 인덱스 구조 확인
            index_name = index.__class__.__name__

            # IDSelectorBatch 사용 (IDSelectorBitmap은 FAISS 1.11.0에서 버그가 있음)
            include_ids_array = np.array(valid_include_ids, dtype=np.int64)
            id_selector = faiss.IDSelectorBatch(len(include_ids_array), faiss.swig_ptr(include_ids_array))

            # 인덱스 타입에 맞는 SearchParameters 설정
            if 'IVF' in index_name or hasattr(index, 'nprobe'):
                # IVF 계열 인덱스
                params = faiss.SearchParametersIVF()
                params.sel = id_selector
                params.nprobe = max(getattr(index, 'nprobe', 100), 100)
            else:
                # Flat 등 다른 인덱스
                params = faiss.SearchParameters()
                params.sel = id_selector

            # 검색 실행
            D, I = index.search(query_vector.astype('float32'), k, params=params)

            # logging.info(f"[DEBUG] Search completed. D shape: {D.shape}, I shape: {I.shape}")
            # logging.info(f"[DEBUG] D values: {D[0]}")
            # logging.info(f"[DEBUG] I values (before threshold): {I[0]}")
            logging.info(f"search_with_include [{key}]: {len(valid_include_ids)} include_ids, returned {I} results")            

            # 기존 search와 동일한 threshold 필터링 적용
            if key in ['artist', 'lyrics', 'title']:
                threshold = 0.9
                mask = D > threshold
                D[mask] = np.inf
                I[mask] = -1

            return D, I

        except Exception as e:
            logging.error(f"Error in search_with_include for {key}: {e}")
            logging.warning("Attempting fallback to post-filtering method")

            # Fallback: 전체 검색 후 필터링
            try:
                include_set = set(include_ids)
                search_k = min(k * 10, index.ntotal)
                D, I = index.search(query_vector.astype('float32'), search_k)

                # 결과 필터링
                mask = np.isin(I[0], list(include_set))
                filtered_D = D[0][mask][:k]
                filtered_I = I[0][mask][:k]

                # 2D 배열로 변환
                result_D = filtered_D.reshape(1, -1)
                result_I = filtered_I.reshape(1, -1)

                logging.info(f"Fallback method returned {result_I.shape[1]} results")
                return result_D, result_I

            except Exception as fallback_error:
                logging.error(f"Fallback method also failed: {fallback_error}")
                return None, None

    @staticmethod
    def get_info(index_type: str) -> Optional[Dict]:
        """특정 인덱스의 정보 반환"""
        if index_type not in MuseFaiss.indices:
            return None

        try:
            index = MuseFaiss.indices[index_type]
            return {
                'type': index_type,
                'ntotal': index.ntotal,
                'd': index.d,
                'is_trained': getattr(index, 'is_trained', True),
                'nlist': getattr(index, 'nlist', None)
            }
        except Exception as e:
            logging.error(f"Error getting info for {index_type}: {e}")
            return None
    
    @staticmethod
    def get_all_info() -> Dict:
        """모든 인덱스 정보 반환"""
        try:
            
            return {
                index_type: MuseFaiss.get_info(index_type) 
                for index_type in MuseFaiss.indices.keys()
            }
        except Exception as e:
            return {
                "error": e
            }