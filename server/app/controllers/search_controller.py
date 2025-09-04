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

@router.post("/text")
async def search_song(input_data: TextRequest):    
    text = input_data.text    
    mood = input_data.mood        
    start = time.time()
    result = await SearchService.search_text(text=text, mood=mood)
    logging.info(f'''소요시간: {time.time()-start}''')
    return result