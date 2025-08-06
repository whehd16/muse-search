from config import DATABASE_CONFIG
import pymysql
import logging
from pymysqlpool import ConnectionPool

class Database:    
    __pool = ConnectionPool(size=100, name="db_pool", **DATABASE_CONFIG[0])

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
            return e, 500
        finally:
            Database.__close(connection)