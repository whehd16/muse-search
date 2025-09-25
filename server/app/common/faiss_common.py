import faiss
import numpy as np
import logging
from typing import Dict, Tuple, Optional
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
        logging.info(f"Loaded lyrics index: {indices['vibe'].ntotal} vectors")
    except Exception as e:
        logging.warning(f"Failed to load lyrics index, trying backup: {e}")
        try:
            indices['lyrics'] = faiss.read_index(f'{INDEX_PATH}/muse_lyrics_backup.index')
        except Exception as e2:
            logging.error(f"Failed to load lyrics backup index: {e2}")

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