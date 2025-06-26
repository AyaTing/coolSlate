from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
from google.auth.transport import requests
from google.oauth2 import id_token as google_id_token
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from utils.dependencies import get_connection
import asyncpg

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

JWT_KEY = os.getenv("JWT_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: asyncpg.Connection = Depends(get_connection),
):
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            return None
        select_query = "SELECT * FROM users WHERE id = $1"
        user_data = await db.fetchrow(
            select_query,
            user_id,
        )
        if not user_data:
            return None
        return dict(user_data) if user_data else None
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
    except Exception as e:
        print(f"無法取得現在的使用者資訊出現錯誤: {e}")
        return None


async def require_auth(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="需要登入才能使用此功能")
    return current_user


async def require_admin(admin_user: dict = Depends(require_auth)):
    if admin_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理員權限")
    return admin_user


async def verify_google_token(id_token: str):
    try:
        id_info = google_id_token.verify_oauth2_token(
            id_token, requests.Request(), GOOGLE_CLIENT_ID
        )
        if not id_info.get("email_verified", False):
            raise HTTPException(status_code=401, detail="Google 帳號 email 未驗證")
        required_fields = ["sub", "email"]
        for field in required_fields:
            if not id_info.get(field):
                raise HTTPException(
                    status_code=401, detail=f"Token 缺少必要欄位: {field}"
                )
        return id_info
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"無效的 Google Token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Token 驗證失敗: {str(e)}")


def create_jwt_token(user_id):
    expired_at = datetime.now(tz=TAIPEI_TZ) + timedelta(days=7)
    payload = {"user_id": user_id, "iat": datetime.now(tz=TAIPEI_TZ), "exp": expired_at}
    token = jwt.encode(payload, JWT_KEY, algorithm="HS256")
    return token


async def verify_order_ownership(order_id: int, user_id: int, db):
    try:
        select_query = "SELECT id FROM orders WHERE id = $1 AND user_id = $2"
        order = await db.fetchrow(select_query, order_id, user_id)
        if not order:
            raise HTTPException(status_code=403, detail="無權操作此訂單")
        return True
    except Exception as e:
        print(f"訂單權限查詢失敗: {e}")
        raise HTTPException(status_code=500, detail="訂單權限查詢失敗")
