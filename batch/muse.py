import logging
import os
import argparse
import math
import numpy as np
from datetime import datetime
from common.logger_common import Logger
from common.dataloader_common import MuseDataLoader
from common.faiss_common import MuseFaiss
from common.playlist_common import PlaylistLoader

Logger.set_logger(log_path='./logs', file_name='etc.log')

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest='func', required=True, help="select batch function")

        # train parser
        train_parser = subparsers.add_parser('train_faiss', help='Train a FAISS')
        train_parser.add_argument('--model', type=str, required=True, help='Select a model')
        train_parser.add_argument('--type', type=str, required=True, help='Select a type(song, artist, song_name)')
        train_parser.add_argument('--output', type=str, required=True, help='Output file path')
        train_parser.add_argument('--dimension', type=int, required=True, help='dimension of model')

        # add parser
        vector_add_parser = subparsers.add_parser('add_faiss', help='Add vectors into pre-clustered FAISS')
        vector_add_parser.add_argument('--model', type=str, required=True, help='Select a model')
        vector_add_parser.add_argument('--type', type=str, required=True, help='Select a type(song, artist, song_name)')
        vector_add_parser.add_argument('--dimension', type=int, required=True, help='dimension of model')
        vector_add_parser.add_argument('--input', type=str, required=True, help='Input file path')
        vector_add_parser.add_argument('--output', type=str, required=True, help='Output file path')

        # add daily parser
        daily_add_parser = subparsers.add_parser('add_daily_faiss', help='Add daily new vectors into existing FAISS index')
        daily_add_parser.add_argument('--model', type=str, required=True, help='Select a model')
        daily_add_parser.add_argument('--type', type=str, required=True, help='Select a type(song, artist, song_name)')
        daily_add_parser.add_argument('--dimension', type=int, required=True, help='dimension of model')
        daily_add_parser.add_argument('--input', type=str, required=True, help='Input file path (existing FAISS index)')
        daily_add_parser.add_argument('--output', type=str, required=True, help='Output file path')

        #info parer
        info_add_parser = subparsers.add_parser('info_faiss', help='info faiss index')
        info_add_parser.add_argument('--dimension', type=int, required=True, help='dimension of model')
        info_add_parser.add_argument('--input', type=str, required=True, help='Input file path')

        # cache_playlist parser (NEW!)
        cache_playlist_parser = subparsers.add_parser('cache_playlist', help='Cache playlist include_ids to Redis (permanent)')

        args = parser.parse_args()

        log_path = f'''./logs/{args.func}'''

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        if args.func == 'train_faiss':
            Logger.set_logger(log_path=log_path, file_name= f'''train_{args.model}.log''')
 
            train_vectors = MuseDataLoader.get_train_vectors(model=args.model, embedding_type=args.type)

            if train_vectors:
                muse_faiss = MuseFaiss(d=args.dimension)
                muse_faiss.set_index(nlist=int(math.sqrt(len(train_vectors))))
                logging.info(f'''벡터 학습 중...''')
                muse_faiss.train(vectors=np.array(train_vectors, dtype='float32'))
                logging.info(f'''벡터 학습 완료''')
                muse_faiss.write_index(args.output)                
                logging.info(f'''벡터 cluster 생성 완료''')

        elif args.func == 'add_faiss':
            Logger.set_logger(log_path=log_path, file_name=f'''add_{args.model}.log''')            
            
            muse_faiss = MuseFaiss(d=args.dimension)
            muse_faiss.read_index(args.input)
            
            last_idx = MuseDataLoader.get_last_idx(model=args.model, embedding_type=args.type)

            for i in range(1, last_idx, 5000):
                add_vectors  = MuseDataLoader.get_add_vectors(model=args.model, embedding_type=args.type, start_idx=i, end_idx=min(last_idx, i+5000))
                muse_faiss.add(vectors=np.array(add_vectors, dtype='float32'))
                logging.info(f'''ADD COMPLETE({len(add_vectors)}) {i} ~ {min(last_idx, i+5000-1)}''')
                logging.info(f'''{muse_faiss.info()}''')

            muse_faiss.write_index(args.output)
            
        elif args.func == 'add_daily_faiss':
            Logger.set_logger(log_path=log_path, file_name=f'''add_daily_{args.model}.log''')

            muse_faiss = MuseFaiss(d=args.dimension)
            muse_faiss.read_index(args.input)

            # 기존 인덱스에 저장된 벡터 개수 확인
            current_ntotal = muse_faiss.ntotal()
            logging.info(f'''현재 FAISS 인덱스에 저장된 벡터 수: {current_ntotal}''')
            logging.info(f'''DB idx 1~{current_ntotal}까지 이미 FAISS에 저장됨 (FAISS index 0~{current_ntotal-1})''')

            # DB의 마지막 인덱스 확인
            last_idx = MuseDataLoader.get_last_idx(model=args.model, embedding_type=args.type)
            logging.info(f'''DB의 마지막 idx: {last_idx}''')

            # 이미 추가된 부분은 건너뛰고, 새로운 부분만 추가
            # DB idx는 1부터 시작, FAISS는 0부터 시작하므로
            # ntotal이 N이면 DB idx 1~N이 FAISS index 0~N-1에 저장된 것
            start_from = current_ntotal + 1

            if start_from > last_idx:
                logging.info(f'''추가할 새로운 벡터가 없습니다. (FAISS에 저장된 DB idx: 1~{current_ntotal}, DB 최신 idx: {last_idx})''')
            else:
                logging.info(f'''DB idx {start_from}부터 {last_idx}까지 추가 시작''')

                for i in range(start_from, last_idx + 1, 5000):
                    add_vectors = MuseDataLoader.get_add_vectors(model=args.model, embedding_type=args.type, start_idx=i, end_idx=min(last_idx + 1, i+5000))
                    if add_vectors:
                        muse_faiss.add(vectors=np.array(add_vectors, dtype='float32'))
                        logging.info(f'''ADD COMPLETE({len(add_vectors)}) DB idx {i} ~ {min(last_idx, i+5000-1)}''')
                        logging.info(f'''{muse_faiss.info()}''')
                    else:
                        logging.warning(f'''범위 DB idx {i} ~ {min(last_idx, i+5000-1)}에 추가할 벡터가 없습니다''')

            muse_faiss.write_index(args.output)
            logging.info(f'''인덱스 저장 완료: {args.output}''')

        elif args.func =='info_faiss':
            Logger.set_logger(log_path=log_path, file_name='info.log')
            muse_faiss = MuseFaiss(d=args.dimension)
            muse_faiss.read_index(args.input)
            logging.info(f'''{muse_faiss.info()}''')

        elif args.func == 'cache_playlist':
            Logger.set_logger(log_path=log_path, file_name='cache_playlist.log')
            logging.info(f'''Starting playlist cache job (permanent storage)''')
            PlaylistLoader.load_all_programs_to_redis()
            logging.info(f'''Playlist cache job completed''')

        else:
            os.rmdir(f'''./logs/{args.func}''')
            logging.error(f'''{args.func} is not a func''')

    except Exception as e:
        logging.error(e)

