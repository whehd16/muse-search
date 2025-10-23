import redis
import logging
import json
from typing import Optional, List
from config import REDIS_CONFIG

class RedisClient:
    """Redis 클라이언트 (배치용)"""
    _client: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Redis 클라이언트 인스턴스 반환 (싱글톤)"""
        if cls._client is None:
            try:
                cls._client = redis.Redis(**REDIS_CONFIG)
                # 연결 테스트
                cls._client.ping()
                logging.info("Redis connection established")
            except Exception as e:
                logging.error(f"Failed to connect to Redis: {e}")
                raise
        return cls._client

    @classmethod
    def close(cls):
        """Redis 연결 종료"""
        if cls._client:
            cls._client.close()
            cls._client = None
            logging.info("Redis connection closed")

    @staticmethod
    def set_playlist_include_ids(key: str, playlist_id: str, include_ids: List[int]):
        """
        Redis에 playlist의 include_ids 저장 (영구 저장)

        Args:
            key: 테이블 타입 (vibe, title, artist, etc.)
            playlist_id: 플레이리스트 ID
            include_ids: FAISS idx 리스트

        Example:
            >>> RedisClient.set_playlist_include_ids('vibe', 'drp', [0, 15, 234])
            Redis key: playlist_idx:drp_vibe
        """
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_idx:{playlist_id}_{key}"

            # List[int] → JSON 문자열 변환
            value = json.dumps(include_ids)

            # 영구 저장 (TTL 없음)
            client.set(redis_key, value)
            logging.info(f"Cache SET: {redis_key} ({len(include_ids)} ids, permanent)")
        except Exception as e:
            logging.error(f"Error setting playlist include_ids to Redis: {e}")

    @staticmethod
    def delete_playlist_include_ids(key: str, playlist_id: str):
        """
        Redis에서 playlist의 include_ids 삭제 (캐시 무효화)

        Args:
            key: 테이블 타입
            playlist_id: 플레이리스트 ID
        """
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_idx:{playlist_id}_{key}"
            client.delete(redis_key)
            logging.info(f"Cache DELETED: {redis_key}")
        except Exception as e:
            logging.error(f"Error deleting playlist include_ids from Redis: {e}")

    @staticmethod
    def delete_all_playlist_cache(playlist_id: str):
        """
        특정 playlist의 모든 key 캐시 삭제

        Args:
            playlist_id: 플레이리스트 ID
        """
        try:
            client = RedisClient.get_client()
            pattern = f"playlist_idx:{playlist_id}_*"

            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                logging.info(f"Deleted {len(keys)} cache entries for playlist {playlist_id}")
        except Exception as e:
            logging.error(f"Error deleting all playlist cache: {e}")

    @staticmethod
    def set_last_update_time(playlist_id: str, timestamp: float):
        """특정 playlist의 마지막 갱신 시간 저장"""
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_update:{playlist_id}"
            client.set(redis_key, timestamp)
            logging.info(f"Set last update time for {playlist_id}: {timestamp}")
        except Exception as e:
            logging.error(f"Error setting last update time: {e}")

    @staticmethod
    def get_last_update_time(playlist_id: str) -> Optional[float]:
        """특정 playlist의 마지막 갱신 시간 조회"""
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_update:{playlist_id}"
            timestamp = client.get(redis_key)
            if timestamp:
                return float(timestamp)
            return None
        except Exception as e:
            logging.error(f"Error getting last update time: {e}")
            return None

    @staticmethod
    def get_all_cache_keys(pattern: str = "playlist_idx:*") -> List[str]:
        """
        패턴에 맞는 모든 캐시 키 조회

        Args:
            pattern: Redis key 패턴

        Returns:
            키 리스트
        """
        try:
            client = RedisClient.get_client()
            keys = client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logging.error(f"Error getting cache keys: {e}")
            return []

    @staticmethod
    def flush_all_cache():
        """모든 캐시 삭제 (주의!)"""
        try:
            client = RedisClient.get_client()
            client.flushdb()
            logging.warning("All cache flushed!")
        except Exception as e:
            logging.error(f"Error flushing cache: {e}")
