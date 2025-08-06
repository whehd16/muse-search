from common.faiss_common import MuseFAISS
from common.mysql_common import Database
from common.oracle_common import OracleDB
from common.llm_common import MuseLLM
import requests
import json
import numpy as np
import sys

if __name__ == "__main__":
    muse_faiss = MuseFAISS(d=1024)
    muse_faiss.read_index('../../batch/index/20250805_bgem3_artist.index')

    # data = {
    #     "text": "A cinematic score with emotional strings and slow build, great for touching listener letters or heartfelt stories."
    # }
    
    while True:
        # # BGEM3
        # data = {
        #         "text": sys.stdin.readline().strip().lower().replace(' ','')
        #     }   
            
        # url = 'http://192.168.170.151:13373/embedding/bgem3'

        # res = requests.post(url, json=data)
        # res = json.loads(res.text)
        # vector = np.array([res['results']], dtype='float32')

        # D, I = muse_faiss.search(vector)           
        # try:
        #     OracleDB.initialize_pool()

        #     for i, idx in enumerate(I[0]):
        #         result, code = Database.execute_query(f"SELECT artist, song_name FROM muse.tb_embedding_bgem3_artist_h WHERE idx = {idx+1}", fetchone=True)
        #         artist, song_name = result[0], result[1]
        #         print(f'''\tDIS: {D[0][i]}, ARTIST: {artist}, 'SONG_NAME': {song_name}''')                    
        # except Exception as e:
        #     print(e)
        # finally:
        #     OracleDB.close_pool()
        
        # continue
            
        # CLAP
        text = sys.stdin.readline().strip()

        print(f'''입력 텍스트:"{text}"''')
        llm_results = MuseLLM.get_request(text=text)

        llm_results = json.loads(llm_results)
        print(type(llm_results), llm_results)
        continue

        for llm_result in llm_results:
            print(f'''LLM(번역&요약): {llm_result}''')
            data = {
                "text": llm_result.strip()
            }   
            
            url = 'http://192.168.170.151:13373/embedding'

            res = requests.post(url, json=data)
            res = json.loads(res.text)
            vector = np.array([res['results']], dtype='float32')
            
            #vector는 자연어를 CLAP으로 임베딩 시킨거...
            D, I = muse_faiss.search(vector)    
            try:
                OracleDB.initialize_pool()

                for idx in I[0]:
                    result, code = Database.execute_query(f"SELECT disccommseq, trackno, chunk_num FROM muse.tb_embedding_clap_h WHERE idx = {idx+1}", fetchone=True)
                    disc_comm_seq, track_no, chunk_num = result[0], result[1], result[2]                       
                    result = OracleDB.execute_query(f"""SELECT A.ARTIST, A.PLAYER, A.BAND_NAME, A.SONG_NAME, A.PLAY_TIME, B.DISC_NAME FROM MIBIS.MI_SONG_INFO A JOIN MIBIS.MI_DISC_INFO B ON A.DISC_COMM_SEQ = B.DISC_COMM_SEQ WHERE A.DISC_COMM_SEQ={result[0]} AND A.TRACK_NO='{result[1]}'""")
                    if result:
                        result = result[0]
                    else:
                        continue                                                        
                    # print(f'''\tARTIST: {result['artist']}, 'SONG_NAME': {result['song_name']}, 'PLAYER': {result['player']}, 'BAND_NAME': {result['band_name']}, 'PLAY_TIME': {result['play_time']}, 'ALBUM_NAME': {result['disc_name']}, 'DISC_COMM_SEQ': {disc_comm_seq}, 'TRACK_NO': {track_no}, 'CHUNK_NUM': {chunk_num}''')                    
                    print(f'''\tARTIST: {result['artist']}, 'SONG_NAME': {result['song_name']}, 'DISC_COMM_SEQ': {disc_comm_seq}, 'TRACK_NO': {track_no}, 'CHUNK_NUM': {chunk_num}''')                    
            except Exception as e:
                print(e)
            finally:
                OracleDB.close_pool()
