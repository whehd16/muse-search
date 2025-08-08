import requests
import numpy as np
import json

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
        'vibe': {
            'embedding_model': 'clap'
        }
    }

    @staticmethod
    def get_vector(key: str, text: str) -> np.ndarray:
        embedding_url = EmbeddingService.embedding_requests_info[EmbeddingService.embedding_info[key]['embedding_model']]['url']
        embedding_body = EmbeddingService.embedding_requests_info[EmbeddingService.embedding_info[key]['embedding_model']]['body']
        embedding_body['text'] = text
        res = requests.post(url=embedding_url, json=embedding_body)
        res = json.loads(res.text)        
        vector = np.array([res['results']], dtype='float32')
        # print(len(vector[0]), embedding_url, text)
        return vector