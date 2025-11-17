from common.mysql_common import Database
import logging
import pickle
import torch
import io
import numpy as np

class MuseDataLoader:
    _selected_mod = [1, 21, 41, 61, 81]
    _table_name = 'muse.tb_embedding_{0}_{1}_h'        
    _mod_select_window_size = 5000
    _table_names = {
        'clap_song': 'muse.tb_embedding_clap_h',
        'clap_lyrics_summary': 'muse.tb_embedding_clap_lyrics_summary_h',
        'bgem3_artist': 'muse.tb_embedding_bgem3_artist_h',
        'bgem3_song_name': 'muse.tb_embedding_bgem3_song_name_h',
        'bgem3_lyrics_slide': 'muse.tb_embedding_bgem3_lyrics_slide_h',
        'bgem3_lyrics_3_slide': 'muse.tb_embedding_bgem3_lyrics_3_slide_h',
        'bgem3_album_name': 'muse.tb_embeddingbgem3_album_name_h'
    }
    _columns = {
        'clap_song': 'embedding_result',
        'clap_lyrics_summary': 'embedding_result',
        'bgem3_artist': 'artist_embedding',
        'bgem3_song_name': 'song_name_embedding',
        'bgem3_lyrics_slide': 'embedding_result',
        'bgem3_lyrics_3_slide': 'embedding_result',
        'bgem3_album_name': 'album_name_embedding'
    }

    @staticmethod
    def get_last_idx(model, embedding_type):
        try:
            table_key = f'{model}_{embedding_type}'
            table_name = MuseDataLoader._table_names.get(table_key)

            if not table_name:
                logging.error(f'''MuseDataLoader.get_last_idx: Unknown table key {table_key}''')
                return None

            result, code = Database.execute_query(
                f'''
                    SELECT idx
                    FROM {table_name}
                    ORDER BY idx DESC LIMIT 1
                ''', fetchone=True
            )

            if code == 200:
                logging.info(f'''MuseDataLoader.get_last_idx: {result[0]} ''')
                return result[0]
            else:
                logging.error("MuseDataLoader.get_last_idx: FAILED TO GET VECTOR COUNT")
                return None
        except Exception as e:
            logging.error(f'''MuseDataLoader.get_last_idx: {e}''')
    
    @staticmethod
    def get_train_vectors(model, embedding_type):
        try:
            table_key = f'{model}_{embedding_type}'
            table_name = MuseDataLoader._table_names.get(table_key)
            column_name = MuseDataLoader._columns.get(table_key)

            if not table_name or not column_name:
                logging.error(f'''MuseDataLoader.get_train_vectors: Unknown table key {table_key}''')
                return None

            last_idx = MuseDataLoader.get_last_idx(model=model, embedding_type=embedding_type)
            train_vectors=[]
            if not last_idx:
                return
            else:
                for i in range(1, last_idx+1, MuseDataLoader._mod_select_window_size):
                    results, code = Database.execute_query(
                        f'''
                            SELECT idx, {column_name}
                            FROM {table_name}
                            WHERE idx_mod_100 in ({','.join(list(map(str, MuseDataLoader._selected_mod)))})
                            AND idx >= %s and idx < %s
                        ''', params=(i, min(last_idx, i+MuseDataLoader._mod_select_window_size)), fetchall=True
                    )
                    if code == 200:
                        logging.info(f'''MuseDataLoader.get_train_vectors: load vectors in [{','.join(list(map(str, MuseDataLoader._selected_mod)))}] in range ({i} ~ {min(last_idx, i+MuseDataLoader._mod_select_window_size)})''')
                        for res in results:
                            train_vectors.append(np.atleast_2d(np.load(io.BytesIO(res[1]), allow_pickle=True))[0])
                    else:
                        logging.error("MuseDataLoader.get_train_vetctors: FAILED TO GET TRAIN VECTORS")
            return train_vectors
        except Exception as e:
            logging.error(f'''MuseDataLoader.get_train_vetctors: {e}''')
            return None

    @staticmethod
    def get_add_vectors(model, embedding_type, start_idx, end_idx):
        try:
            table_key = f'{model}_{embedding_type}'
            table_name = MuseDataLoader._table_names.get(table_key)
            column_name = MuseDataLoader._columns.get(table_key)

            if not table_name or not column_name:
                logging.error(f'''MuseDataLoader.get_add_vectors: Unknown table key {table_key}''')
                return None

            add_vectors = []
            results, code = Database.execute_query(
                f'''
                    SELECT idx, {column_name}
                    FROM {table_name}
                    WHERE idx >= %s and idx < %s
                ''', params=(start_idx, end_idx), fetchall=True
            )

            if code == 200:
                for res in results:
                    add_vectors.append(np.atleast_2d(np.load(io.BytesIO(res[1]), allow_pickle=True))[0])
            return add_vectors
        except Exception as e:
            logging.error(e)
            return None


            