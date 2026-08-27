from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.rag import router as rag_router
from app.statistics import router as statistics_router

app = FastAPI(title="Call Statistics API", version="0.1.0")
app.include_router(router)
app.include_router(statistics_router)
app.include_router(rag_router)

web_dir = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=web_dir), name="static")


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(web_dir / "dashboard.html")
