from common.mysql_backup_common import Database

class PlaylistDAO:
    _playlist_table_name = 'tb_song_{0}_m'

    @staticmethod
    def get_playlist_info(playlist_id: str):
        playlist_info = []
        table_name = PlaylistDAO._playlist_table_name.format(playlist_id)
        results, code = Database.execute_query(f"""
            SELECT disc_id, track_no 
            FROM {table_name}
        """, fetchall=True)

        if code == 200:
            playlist_info = [(result[0].strip(), result[1].strip()) for result in results]

        return playlist_info
