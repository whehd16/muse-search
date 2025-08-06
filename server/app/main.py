from fastapi import FastAPI, Request
from controllers import faiss_controller, health_controller
from common.oracle_common import OracleDB
from common.faiss_common import MuseekFaiss
from common.health_common import HealthCheck
from config import API_NAME
from error_handler import setup_exception_handlers
import logging

logging.basicConfig(filename='/data1/museek-search/server/app/logs/service.log', format = '%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)

app = FastAPI(title=f'''{API_NAME} API''')

setup_exception_handlers(app)

@app.on_event("startup")
async def startup():
    try:
        logging.info("Server Start")
        ivfpq_info, code = MuseekFaiss.ivfpq_info()              
        if code == 200:            
            logging.info(f"FAISS ON: {ivfpq_info['ntotal']}")
        OracleDB.initialize_pool()
    except Exception as e:        
        logging.error(e)
    finally:
        HealthCheck.init(f'''{API_NAME}''')

@app.on_event("shutdown")
async def shutdown():
    try:
        logging.info("Server Close")                
        OracleDB.close_pool()        
    except Exception as e:
        logging.error(e)

# 컨트롤러 라우터 등록
app.include_router(faiss_controller.router)
app.include_router(health_controller.router)