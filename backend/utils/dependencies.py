import asyncpg
from fastapi import Request, HTTPException
import httpx


async def get_connection(request: Request):
    if not hasattr(request.app.state, "db_pool") or not request.app.state.db_pool:
        print("無法取得資料庫連線池")
        raise HTTPException(status_code=503, detail="資料庫服務不可用")
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as connection:
        yield connection


async def get_http_client(request: Request):
    if (
        not hasattr(request.app.state, "http_client")
        or not request.app.state.http_client
    ):
        print("無法取得 HTTP 連線")
        raise HTTPException(status_code=503, detail="httpx.AsyncClient 服務不可用")
    client: httpx.AsyncClient = request.app.state.http_client
    return client
