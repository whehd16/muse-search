from fastapi import APIRouter
from services.faiss_service import FaissService
from services.search_service import SearchService
from common.response_common import success_response, error_response
from pydantic import BaseModel
from typing import List
import time
import logging

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

class TextRequest(BaseModel):
    text: str
    mood: list

class SimilarRequest(BaseModel):
    disccommseq: int
    trackno: str

class AnalyzeRequest(BaseModel):
    text: str
    llm_result: dict
    disccommseq: int
    trackno: str

@router.post("/text")
async def search_song(input_data: TextRequest):    
    text = input_data.text    
    mood = input_data.mood        
    start = time.time()
    logging.info(f'''User Query: {text}''')
    result = await SearchService.search_text(text=text, mood=mood)
    logging.info(f'''소요시간: {time.time()-start}''')
    return result

@router.post("/similar")
async def search_song(input_data: SimilarRequest):
    disccommseq = input_data.disccommseq
    trackno = input_data.trackno
    start = time.time()
    logging.info(f'''Find Similar: {disccommseq}_{trackno} ''')
    result = await SearchService.search_similar_song(key='vibe', disccommseq=disccommseq, trackno=trackno)
    logging.info(f'''소요시간: {time.time()-start}''')
    return result

@router.post("/analyze")
async def analyze_result(input_data: AnalyzeRequest):
    text = input_data.text
    llm_result = input_data.llm_result
    disccommseq = input_data.disccommseq
    trackno = input_data.trackno

    result = await SearchService.search_analyze_result(text=text, llm_result=llm_result, disccommseq=disccommseq, trackno=trackno)
    return result

