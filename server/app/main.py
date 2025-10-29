from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from controllers import search_controller
from common.oracle_common import OracleDB
from common.faiss_common import MuseFaiss
from config import API_NAME, BASE_LOG_PATH
from common.logger_common import Logger
import logging

Logger.set_logger(log_path=BASE_LOG_PATH, file_name='service.log')

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup
    try:
        logging.info("Server Start")
        logging.info(MuseFaiss.get_all_info())
        # if code == 200:
        #     logging.info(f"FAISS ON: {ivfpq_info['ntotal']}")
        OracleDB.initialize_pool()
    except Exception as e:
        logging.error(e)

    yield

    # Shutdown
    try:
        logging.info("Server Close")
        OracleDB.close_pool()
    except Exception as e:
        logging.error(e)

app = FastAPI(title=f'''{API_NAME} API''', lifespan=lifespan)

# 컨트롤러 라우터 등록
app.include_router(search_controller.router)