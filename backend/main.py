from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.database import close_pool, create_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_pool = None
    try:
        db_pool = await create_pool()
        app.state.db_pool = db_pool
        yield
    except Exception as e:
        print(f"資料庫啟動失敗：{e}")
        app.state.db_pool = None
    finally:
        if app.state.db_pool:
            await close_pool(app.state.db_pool)
            app.state.db_pool = None


app = FastAPI(lifespan=lifespan)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port= 8000)