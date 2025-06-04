from fastapi import APIRouter, HTTPException, Depends, Body 
from utils.dependencies import get_connection
from utils.auth import require_auth, require_admin
from services.auth_service import google_login_service
from models.auth_model import LoginResponse, User
import asyncpg


router = APIRouter(prefix="/api", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(id_token: str = Body(...), db: asyncpg.Connection = Depends(get_connection)):
    try:
        return await google_login_service(id_token, db)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Google 登入服務錯誤: {e}")
        raise HTTPException(status_code=500, detail="登入處理失敗，請稍後再試")


@router.get("/user", response_model=User)
async def get_user(current_user = Depends(require_auth)):
    return User(**current_user)

@router.get("/admin", response_model=User)
async def check_admin(admin_user = Depends(require_admin)):
    return User(**admin_user)

@router.post("/logout")
async def logout(current_user = Depends(require_auth)):
    return {"message": "登出成功"}
