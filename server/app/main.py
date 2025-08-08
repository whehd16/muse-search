from fastapi import FastAPI, Request
from controllers import search_controller
from common.oracle_common import OracleDB
from common.faiss_common import MuseFaiss
from config import API_NAME, BASE_LOG_PATH
from common.logger_common import Logger
import logging

app = FastAPI(title=f'''{API_NAME} API''')

Logger.set_logger(log_path=BASE_LOG_PATH, file_name='service.log')

@app.on_event("startup")
async def startup():
    try:                
        logging.info("Server Start")
        logging.info(MuseFaiss.get_all_info())
        # if code == 200:            
        #     logging.info(f"FAISS ON: {ivfpq_info['ntotal']}")
        OracleDB.initialize_pool()
    except Exception as e:        
        logging.error(e)    

@app.on_event("shutdown")
async def shutdown():
    try:
        logging.info("Server Close")                
        OracleDB.close_pool()        
    except Exception as e:
        logging.error(e)

# 컨트롤러 라우터 등록
app.include_router(search_controller.router)