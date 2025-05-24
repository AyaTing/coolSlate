from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from db.database import close_pool, create_pool
from fastapi.middleware.cors import CORSMiddleware
from routers import auth_router, calendar_router
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.db_pool = await create_pool()
        app.state.http_client = httpx.AsyncClient(timeout=10.0)
        yield
    except Exception as e:
        print(f"服務啟動失敗：{e}")
        app.state.db_pool = None
        app.state.http_client = None
    finally:
        if app.state.db_pool:
            await close_pool(app.state.db_pool)
            app.state.db_pool = None
        if app.state.http_client:
            await app.state.http_client.aclose()
            app.state.http_client = None


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(calendar_router.router)

@app.get("/status")
async def check_status():
    if not app.state.db_pool or not app.state.http_client:
        raise HTTPException(status_code=500, detail="後端服務無法使用")
    return {"status": "success", "message": "後端服務正常運行"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
