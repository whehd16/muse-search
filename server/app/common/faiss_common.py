import faiss
import numpy as np

class MuseFAISS:
    def __init__(self, d=512):
        self.quantizer = faiss.IndexHNSWFlat(d, 32)
        self.d = d
        self.index = None
        self.exception_list = [] 
    
    def set_index(self, nlist):
        self.index = faiss.IndexIVFPQ(self.quantizer, self.d, nlist, 16, 8)

    def train(self, vectors):        
        self.index.train(vectors)
    
    def add(self, vectors):        
        self.index.add(vectors)
    
    def search(self, xq, k=1000):
        if self.index:
            D, I = self.index.quantizer.search(xq, k)
            # print(D, I)
            D, I = self.index.search(xq, k)
            # print(D, I)
            return D, I
    
    def write_index(self, path):
        faiss.write_index(self.index, path)

    def read_index(self, path):
        self.index = faiss.read_index(path)

    def info(self):        
        # return 'quantizer:{0}, nlist:{1}, is_trained:{2}, ntotal:{3}, d:{4}'.format(
        #     self.index.quantizer, self.index.nlist, self.index.is_trained, self.index.ntotal, self.index.d
        # )
        return 'nlist:{0}, is_trained:{1}, ntotal:{2}, d:{3}'.format(
            self.index.nlist, self.index.is_trained, self.index.ntotal, self.index.d
        )
    
    def ntotal(self):
         return self.IVFPQ_index.ntotal
    
    def print_all_vectors(self):
        n_total = self.IVFPQ_index.ntotal  # 전체 벡터 수
        if hasattr(self.IVFPQ_index, 'reconstruct_n'):            
            vectors = self.IVFPQ_index.reconstruct_n(0, n_total)
        else:
            vectors = []
            for i in range(n_total):
                vectors.append(self.IVFPQ_index.reconstruct(i))
            vectors = np.array(vectors)
        
        print(f"Total vectors: {n_total}")
        # print(f"Vectors shape: {vectors.shape}")
        # print("Vectors:")
        # print(vectors)

        return vectors