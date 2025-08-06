import logging
import os
import argparse
import math
import numpy as np
from datetime import datetime
from common.logger_common import Logger
from common.dataloader_common import MuseDataLoader
from common.faiss_common import MuseFAISS

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

        #info parer
        info_add_parser = subparsers.add_parser('info_faiss', help='info faiss index')     
        info_add_parser.add_argument('--dimension', type=int, required=True, help='dimension of model')
        info_add_parser.add_argument('--input', type=str, required=True, help='Input file path')

        args = parser.parse_args()

        log_path = f'''./logs/{args.func}'''

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        if args.func == 'train_faiss':
            Logger.set_logger(log_path=log_path, file_name= f'''train_{args.model}.log''')
 
            train_vectors = MuseDataLoader.get_train_vectors(model=args.model, embedding_type=args.type)

            if train_vectors:
                muse_faiss = MuseFAISS(d=args.dimension)                
                muse_faiss.set_index(nlist=int(math.sqrt(len(train_vectors))))
                muse_faiss.train(vectors=np.array(train_vectors, dtype='float32'))
                muse_faiss.write_index(args.output)                

        elif args.func == 'add_faiss':
            Logger.set_logger(log_path=log_path, file_name=f'''add_{args.model}.log''')            
            
            muse_faiss = MuseFAISS(d=args.dimension)
            muse_faiss.read_index(args.input)
            
            last_idx = MuseDataLoader.get_last_idx(model=args.model, embedding_type=args.type)

            for i in range(1, last_idx, 5000):
                add_vectors  = MuseDataLoader.get_add_vectors(model=args.model, embedding_type=args.type, start_idx=i, end_idx=min(last_idx, i+5000))
                muse_faiss.add(vectors=np.array(add_vectors, dtype='float32'))
                logging.info(f'''ADD COMPLETE({len(add_vectors)}) {i} ~ {min(last_idx, i+5000-1)}''')
                logging.info(f'''{muse_faiss.info()}''')

            muse_faiss.write_index(args.output)
            
        elif args.func =='info_faiss':
            Logger.set_logger(log_path=log_path, file_name='info.log')
            muse_faiss = MuseFAISS(d=args.dimension)
            muse_faiss.read_index(args.input)
            logging.info(f'''{muse_faiss.info()}''')
            
        else:
            os.rmdir(f'''./logs/{args.func}''')
            logging.error(f'''{args.func} is not a func''')   
    
    except Exception as e:
        logging.error(e)

