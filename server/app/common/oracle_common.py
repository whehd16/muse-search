from config import ORACLE_DATABASE_CONFIG, ORACLE_DATABASE_PATH
import oracledb
import logging

oracledb.init_oracle_client(lib_dir=ORACLE_DATABASE_PATH)

class OracleDB:
    _pool = None
    _pool_min_size, _pool_max_size = 2, 100

    _dsn = dsn = oracledb.makedsn(
        host=ORACLE_DATABASE_CONFIG['host'],
        port=ORACLE_DATABASE_CONFIG['port'],
        service_name=ORACLE_DATABASE_CONFIG['service_name']
    )

    @staticmethod
    def initialize_pool():
        try:
            if OracleDB._pool is None:
                OracleDB._pool = oracledb.create_pool(
                    user=ORACLE_DATABASE_CONFIG['user_name'],
                    password=ORACLE_DATABASE_CONFIG['password'],
                    dsn=OracleDB._dsn,
                    min=OracleDB._pool_min_size,
                    max=OracleDB._pool_max_size
                )
                logging.info(
                    f"Connection pool initialized. Min: {OracleDB._pool_min_size}, Max: {OracleDB._pool_max_size}"
                )

        except Exception as e:
            logging.error(f"Failed to initialize connection pool: {str(e)}")
            raise

    @staticmethod
    def get_connection():                
        if OracleDB._pool is None:
            raise Exception("Connection pool is not initialized")
        try:
            connection = OracleDB._pool.acquire()            
            return connection
        except Exception as e:
            logging.error(f"Failed to get connection: {str(e)}")
            return None

    @staticmethod
    def release_connection(connection: oracledb.Connection) -> None:        
        if connection:
            try:
                OracleDB._pool.release(connection)                
            except Exception as e:
                logging.error(f"Failed to release connection: {str(e)}")

    @staticmethod
    def close_pool():        
        if OracleDB._pool:
            try:
                OracleDB._pool.close()
                OracleDB._pool = None
                logging.info("Connection pool closed")
            except Exception as e:
                logging.error(f"Failed to close pool: {str(e)}")

    @staticmethod
    def is_pool_initialized() -> bool:        
        return OracleDB._pool is not None

    @staticmethod
    def execute_query(query, params=None):
        connection = None
        try:
            connection = OracleDB.get_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, params or {})
                columns = [col[0].lower() for col in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
        except Exception as e:
            logging.error(f"Failed to execute query: {str(e)}")
            raise
        finally:
            if connection:
                OracleDB.release_connection(connection)