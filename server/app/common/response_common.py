from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

def success_response(data=None, message="Success"):
    return JSONResponse(content=jsonable_encoder({
        "results": data
    }))

def error_response(message="Error", status_code=400):
    return JSONResponse(content={
        "status": "error",
        "message": message
    }, status_code=status_code)
