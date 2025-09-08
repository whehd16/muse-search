import requests
import numpy as np
import json
import logging

class EmbeddingService:
    embedding_requests_info = {
        'bgem3': {
            'url': 'http://192.168.170.151:13373/embedding/bgem3',
            'body': {'text': ''}
        },
        'clap': {
            'url': 'http://192.168.170.151:13373/embedding/clap',
            'body': {'text': ''}
        }
    }

    embedding_info = {
        'artist': {
            'embedding_model': 'bgem3'
        },
        'title': {
            'embedding_model': 'bgem3'
        },
        'lyrics': {
            'embedding_model': 'bgem3'
        },
        'vibe': {
            'embedding_model': 'clap'
        },
        'lyrics_summary':{
            'embedding_model': 'clap'
        }
    }

    @staticmethod
    def get_vector(key: str, text: str) -> np.ndarray:        
        embedding_url = EmbeddingService.embedding_requests_info[EmbeddingService.embedding_info[key]['embedding_model']]['url']
        # 딕셔너리를 복사해서 스레드 안전성 확보
        embedding_body = EmbeddingService.embedding_requests_info[EmbeddingService.embedding_info[key]['embedding_model']]['body'].copy()
        embedding_body['text'] = text.strip()
        res = requests.post(url=embedding_url, json=embedding_body)
        res = json.loads(res.text)        
        vector = np.array([res['results']], dtype='float32')
        # print(len(vector[0]), embedding_url, text)
        return vector