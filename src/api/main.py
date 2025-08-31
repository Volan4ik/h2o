from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..shared.config import settings
from ..shared.db import init_db
from fastapi.staticfiles import StaticFiles
import os
from .routers.webapp import router as webapp_router

app = FastAPI(title="Hydrate API")

if settings.ALLOWED_ORIGINS:
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

init_db()
app.include_router(webapp_router)

@app.get("/health")
def health():
    return {"ok": True}

dist_path = os.path.join(os.path.dirname(__file__), "../../webapp/dist")
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="webapp")