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
    _columns = {
        'clap_song': 'embedding_result',
        'clap_lyrics_summary': 'embedding_result',
        'bgem3_artist': 'artist_embedding',
        'bgem3_song_name': 'song_name_embedding',
        'bgem3_lyrics_slide': 'embedding_result'
    }

    @staticmethod
    def get_last_idx(model, embedding_type):        
        try:
            result, code = Database.execute_query(
                f'''
                    SELECT idx
                    FROM {MuseDataLoader._table_name.format(model, embedding_type)} 
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
            last_idx = MuseDataLoader.get_last_idx(model=model, embedding_type=embedding_type)
            train_vectors=[]
            if not last_idx:
                return
            else:
                for i in range(1, last_idx+1, MuseDataLoader._mod_select_window_size):                   
                    results, code = Database.execute_query(
                        f'''
                            SELECT idx, {MuseDataLoader._columns[f'{model}_{embedding_type}']}
                            FROM {MuseDataLoader._table_name.format(model, embedding_type)} 
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
            add_vectors = []
            results, code = Database.execute_query(
                f'''
                    SELECT idx, {MuseDataLoader._columns[f'{model}_{embedding_type}']}
                    FROM {MuseDataLoader._table_name.format(model, embedding_type)} 
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


            