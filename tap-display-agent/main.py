import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import AgentConfig
from service import DisplayAgentService


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

CONFIG = AgentConfig.load()
SERVICE = DisplayAgentService(CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    SERVICE.start()
    try:
        yield
    finally:
        SERVICE.stop()


app = FastAPI(title="Tap Display Agent", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "tap_id": CONFIG.tap_id,
        "backend_link_lost": SERVICE.is_backend_link_lost(),
    }


@app.get("/local/display/bootstrap")
def get_bootstrap():
    return SERVICE.get_bootstrap_payload()


@app.get("/local/display/runtime")
def get_runtime():
    return SERVICE.read_runtime_payload()


@app.get("/local/display/assets/{asset_id}")
def get_cached_asset(asset_id: str):
    asset_path = SERVICE.get_asset_path(asset_id)
    if asset_path is None:
        raise HTTPException(status_code=404, detail="Cached asset not found")
    return FileResponse(asset_path)


if CONFIG.client_dist_dir.exists():
    app.mount("/display", StaticFiles(directory=CONFIG.client_dist_dir, html=True), name="display")
else:
    @app.get("/display")
    def display_not_built():
        return HTMLResponse(
            """
            <!doctype html>
            <html lang="ru">
              <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>Экран крана</title>
                <style>
                  body { margin: 0; font-family: sans-serif; background: #111827; color: #f3f4f6; display: grid; place-items: center; min-height: 100vh; }
                  main { max-width: 32rem; padding: 2rem; text-align: center; }
                </style>
              </head>
              <body>
                <main>
                  <h1>Сборка клиентского экрана не найдена</h1>
                  <p>Соберите <code>tap-display-client</code> и перезапустите <code>tap-display-agent</code>.</p>
                </main>
              </body>
            </html>
            """
        )
