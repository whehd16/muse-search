import redis
import logging
import json
from typing import Optional, List
from config import REDIS_CONFIG

class RedisClient:
    """Redis 클라이언트 싱글톤"""
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
    def get_playlist_include_ids(key: str, playlist_id: str) -> Optional[List[int]]:
        """
        Redis에서 playlist의 include_ids 조회

        Args:
            key: 테이블 타입 (vibe, title, artist, etc.)
            playlist_id: 플레이리스트 ID

        Returns:
            FAISS idx 리스트 (캐시 없으면 None)

        Example:
            >>> RedisClient.get_playlist_include_ids('vibe', 'drp')
            [0, 15, 234, 567, ...]
            Redis key: playlist_idx:drp_vibe
        """
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_idx:{playlist_id}_{key}"

            value = client.get(redis_key)

            if value is not None:
                # JSON 문자열 → List[int] 변환
                include_ids = json.loads(value)
                logging.info(f"Cache HIT: {redis_key} ({len(include_ids)} ids)")
                return include_ids
            else:
                logging.info(f"Cache MISS: {redis_key}")
                return None
        except Exception as e:
            logging.error(f"Error getting playlist include_ids from Redis: {e}")
            return None

    @staticmethod
    def set_playlist_include_ids(key: str, playlist_id: str, include_ids: List[int], ttl: int = 3600):
        """
        Redis에 playlist의 include_ids 저장

        Args:
            key: 테이블 타입
            playlist_id: 플레이리스트 ID
            include_ids: FAISS idx 리스트
            ttl: TTL (초 단위, 기본 1시간)

        Example:
            >>> RedisClient.set_playlist_include_ids('vibe', 'drp', [0, 15, 234], ttl=3600)
            Redis key: playlist_idx:drp_vibe
        """
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_idx:{playlist_id}_{key}"

            # List[int] → JSON 문자열 변환
            value = json.dumps(include_ids)

            # TTL과 함께 저장
            client.setex(redis_key, ttl, value)
            logging.info(f"Cache SET: {redis_key} ({len(include_ids)} ids, TTL={ttl}s)")
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
    def set_last_update_time(playlist_id: str, timestamp: float):
        """특정 playlist의 마지막 갱신 시간 저장"""
        try:
            client = RedisClient.get_client()
            redis_key = f"playlist_update:{playlist_id}"
            client.set(redis_key, timestamp)
        except Exception as e:
            logging.error(f"Error setting last update time: {e}")
