from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from db.database import close_pool, create_pool
from fastapi.middleware.cors import CORSMiddleware
from routers import (
    calendar_router,
    booking_router,
    payment_router,
    auth_router,
    admin_router,
    product_router
)
from services.background_service import cleanup_loop, repair_scheduling_loop
import asyncio
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.db_pool = await create_pool()
        app.state.http_client = httpx.AsyncClient(timeout=10.0)
        app.state.cleanup = asyncio.create_task(cleanup_loop(app.state.db_pool))
        app.state.repair_scheduler = asyncio.create_task(
            repair_scheduling_loop(app.state.db_pool, app.state.http_client)
        )
        yield
    except Exception as e:
        print(f"服務啟動失敗：{e}")
        app.state.db_pool = None
        app.state.http_client = None
        app.state.cleanup = None
        app.state.repair_scheduler = None
    finally:
        if app.state.db_pool:
            await close_pool(app.state.db_pool)
            app.state.db_pool = None
        if app.state.http_client:
            await app.state.http_client.aclose()
            app.state.http_client = None
        if app.state.cleanup and not app.state.cleanup.done():
            app.state.cleanup.cancel()
        if app.state.repair_scheduler and not app.state.repair_scheduler.done():
            app.state.repair_scheduler.cancel()
        tasks = []
        tasks.append(app.state.cleanup)
        tasks.append(app.state.repair_scheduler)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        app.state.cleanup = None
        app.state.repair_scheduler = None


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://cool-slate.ayating.workers.dev",
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
app.include_router(booking_router.router)
app.include_router(payment_router.router)
app.include_router(admin_router.router)
app.include_router(product_router.router)


@app.get("/status")
async def check_status():
    if (
        not app.state.db_pool
        or not app.state.http_client
        or not app.state.cleanup
        or not app.state.repair_scheduler
    ):
        raise HTTPException(status_code=500, detail="後端服務無法使用")
    return {"status": "success", "message": "後端服務正常運行"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
