from fastapi import FastAPI

from app.api import router
from app.statistics import router as statistics_router

app = FastAPI(title="Call Statistics API", version="0.1.0")
app.include_router(router)
app.include_router(statistics_router)
