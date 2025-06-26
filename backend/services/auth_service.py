from fastapi import HTTPException
from pydantic import EmailStr
from utils.auth import verify_google_token, create_jwt_token
from models.auth_model import LoginResponse, User


async def google_login_service(id_token: str, db):
    try:
        google_user_data = await verify_google_token(id_token)
        google_id = google_user_data["sub"]
        email = google_user_data["email"]
        name = google_user_data.get("name")
        existing_user = await get_user_by_email(email, db)
        if existing_user:
            user_data = await update_user_google_info(existing_user["id"], name, db)
        else:
            user_data = await create_user(email, google_id, name, db)
        token = create_jwt_token(user_data["id"])
        return LoginResponse(user=User(**user_data), token=token)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Google 登入服務錯誤: {e}")
        raise HTTPException(status_code=500, detail="登入處理失敗，請稍後再試")


async def get_user_by_email(email: EmailStr, db):
    try:
        select_query = "SELECT * FROM users WHERE email = $1"
        user_data = await db.fetchrow(select_query, email)
        return dict(user_data) if user_data else None
    except Exception as e:
        print(f"使用者資訊查詢失敗: {e}")
        raise HTTPException(status_code=500, detail="使用者資訊查詢失敗")


async def create_user(email: EmailStr, google_id: str, name: str, db):
    try:
        insert_query = "INSERT INTO users(email, google_id, name, role) VALUES($1, $2, $3, 'customer') RETURNING *"
        user_data = await db.fetchrow(insert_query, email, google_id, name)
        return dict(user_data)
    except Exception as e:
        print(f"使用者資料創建失敗: {e}")
        raise HTTPException(status_code=500, detail="使用者資料創建失敗")


async def update_user_google_info(user_id: str, name: str = None, db=None):
    try:
        update_query = "UPDATE users SET name = COALESCE($1, name), updated_at = NOW() WHERE id = $2 RETURNING *"
        user_data = await db.fetchrow(update_query, name, user_id)
        return dict(user_data)
    except Exception as e:
        print(f"使用者資料更新失敗: {e}")
        raise HTTPException(status_code=500, detail="使用者資料更新失敗")
