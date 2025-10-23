from config import DATABASE_BACKUP_CONFIG, PROGRAM_ID
import pymysql
import logging
from pymysqlpool import ConnectionPool

class Database:    
    __pool = ConnectionPool(size=100, name="db_pool", **DATABASE_BACKUP_CONFIG[0])

    @staticmethod
    def __connect():
        return Database.__pool.get_connection(pre_ping=True)
    
    @staticmethod
    def connect():
        return Database.__pool.get_connection(pre_ping=True)
    
    @staticmethod
    def __close(connection):
        return connection.close()
    
    @staticmethod
    def close(connection):
        return connection.close()
    
    @staticmethod
    def execute_query(query, params=None, fetchone=False, fetchall=False, count_row=False, last_id=False):
        try:
            connection = Database.__connect()
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()

            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            elif count_row:
                if last_id:
                    result = [cursor.rowcount, cursor.lastrowid]
                else:
                    result = cursor.rowcount
            else:
                result = None
            return result, 200
        except Exception as e:
            logging.error(f"Database.execute_query error: {e}")
            return e, 500
        finally:
            Database.__close(connection)

    @staticmethod
    def get_all_program_ids():
        """
        config.py의 PROGRAM_ID 리스트 반환

        Returns:
            program_id 리스트 ['drp', 'fgy', 'k2k', 'mdi', 'nmg', 'rtc']
        """
        logging.info(f"Database.get_all_program_ids: {len(PROGRAM_ID)} programs from config")
        return PROGRAM_ID

    @staticmethod
    def get_program_songs(program_id: str):
        """
        특정 program의 모든 곡 정보 조회
        muse.tb_song_{program_id}_m 테이블에서 조회

        Args:
            program_id: 프로그램 ID (예: 'drp', 'fgy', ...)

        Returns:
            [{'disc_comm_seq': 12345, 'track_no': '01'}, ...]
        """
        try:
            table_name = f"muse.tb_song_{program_id}_m"

            results, code = Database.execute_query(
                f"""
                    SELECT disc_id, track_no
                    FROM {table_name}
                    ORDER BY idx
                """,
                fetchall=True
            )

            if code == 200:
                songs = [
                    {'disc_comm_seq': row[0], 'track_no': row[1]}
                    for row in results
                ]
                logging.info(f"Database.get_program_songs: {len(songs)} songs from {table_name}")
                return songs
            else:
                logging.error(f"Database.get_program_songs: FAILED for {table_name}")
                return []
        except Exception as e:
            logging.error(f"Database.get_program_songs error for program_id={program_id}: {e}")
            return []