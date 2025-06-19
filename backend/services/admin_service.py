from fastapi import HTTPException, UploadFile
from typing import Optional
from services.booking_service import get_user_orders_service
from services.mail_service import send_cancellation_confirmation_email
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import boto3
from botocore.exceptions import ClientError
import uuid
from dotenv import load_dotenv

load_dotenv()

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
else:
    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
    )


async def get_all_orders_service(
    status: Optional[str], payment_status: Optional[str], page: int, limit: int, db
):
    try:
        where_conditions = []
        params = []
        param_count = 0
        if status:
            param_count += 1
            where_conditions.append(f"o.status = ${param_count}")
            params.append(status)
        if payment_status:
            param_count += 1
            where_conditions.append(f"o.payment_status = ${param_count}")
            params.append(payment_status)
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        select_query = f"SELECT COUNT(*) FROM orders o {where_clause}"
        total = await db.fetchval(select_query, *params)

        offset = (page - 1) * limit
        param_count += 1
        limit_param = f"${param_count}"
        param_count += 1
        offset_param = f"${param_count}"

        select_query = f"""
        SELECT o.*, st.name as service_type, u.name as user_name, u.email as user_email
        FROM orders o 
        JOIN service_types st ON o.service_type_id = st.id
        JOIN users u ON o.user_id = u.id
        {where_clause}
        ORDER BY o.created_at DESC
        LIMIT {limit_param} OFFSET {offset_param}
        """
        orders = await db.fetch(select_query, *params, limit, offset)
        result = []
        for order in orders:
            select_query = """
            SELECT preferred_date, preferred_time, contact_name, contact_phone, is_primary, is_selected 
            FROM booking_slots 
            WHERE order_id = $1 
            ORDER BY is_primary DESC, preferred_date, preferred_time
            """
            slots = await db.fetch(select_query, order["id"])
            order_dict = dict(order)
            order_dict["order_id"] = order_dict["id"]
            order_dict["booking_slots"] = [dict(slot) for slot in slots]
            if order_dict["equipment_details"]:
                import json

                order_dict["equipment_details"] = json.loads(
                    order_dict["equipment_details"]
                )
            else:
                order_dict["equipment_details"] = None
            result.append(order_dict)
        return {
            "orders": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        print(f"獲取訂單列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取訂單列表失敗")


async def get_all_users_service(page: int, limit: int, search: Optional[str], db):
    try:
        where_clause = ""
        params = []
        if search:
            where_clause = "WHERE name ILIKE $1 OR email ILIKE $1"
            params.append(f"%{search}%")
        select_query = f"SELECT COUNT(*) FROM users {where_clause}"
        total = await db.fetchval(select_query, *params)
        offset = (page - 1) * limit
        select_query = f"""
        SELECT id, name, email, role, created_at
        FROM users 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        users = await db.fetch(select_query, *params, limit, offset)
        return {
            "users": users,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        print(f"獲取使用者列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取使用者列表失敗")


async def get_user_orders_service_by_admin(user_id: int, db):
    try:
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        orders = await get_user_orders_service(user_id, db)
        return {
            "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
            "orders": orders,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"獲取使用者訂單列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取使用者訂單列表失敗")


async def update_order_refund_status(order_id: int, refund_user: str, db):
    try:
        async with db.transaction():
            select_query = "SELECT id, order_number, status, payment_status, notes FROM orders WHERE id = $1 FOR UPDATE"
            order = await db.fetchrow(
                select_query,
                order_id,
            )
            if not order:
                raise HTTPException(status_code=404, detail="使用者不存在")
            if order["payment_status"] != "paid":
                raise HTTPException(
                    status_code=400, detail="無法對未付款訂單進行此操作"
                )
            if order["status"] in ["completed", "cancelled"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態為 '{order["status"]}'，無法退款"
                )
            refund_time = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M")
            refund_note = f"[退款記錄] 退款人：{refund_user}，退款時間：{refund_time}"
            existing_notes = order["notes"] or ""
            new_notes = existing_notes + refund_note
            update_query = "UPDATE orders SET payment_status = 'refunded', notes = $2, updated_at = NOW() WHERE id = $1"
            await db.execute(update_query, order_id, new_notes)
            return {
                "success": True,
                "message": f"訂單 {order["order_number"]} 退款狀態已更新",
                "refund_user": refund_user,
                "refund_time": refund_time,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"更新退款狀態失敗：{e}")
        raise HTTPException(status_code=500, detail="更新退款狀態失敗")


async def cancel_order(order_id: int, db):
    try:
        async with db.transaction():
            select_query = """
                SELECT o.*, st.name as service_type, st.base_duration_hours, st.additional_duration_hours
                FROM orders o 
                JOIN service_types st ON o.service_type_id = st.id 
                WHERE o.id = $1
                FOR UPDATE
            """
            order = await db.fetchrow(select_query, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            if order["status"] in ["completed", "cancelled"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態為 '{order["status"]}'，無法取消"
                )
            if order["payment_status"] == "unpaid":
                raise HTTPException(
                    status_code=400, detail="未付款訂單會自動清理，無需手動取消"
                )
            if order["payment_status"] != "refunded":
                raise HTTPException(status_code=400, detail="請先執行退款程序")
            if (
                order["service_type"] == "REPAIR"
                and order["status"] == "pending_schedule"
            ):
                update_query = "UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = $1"
                await db.execute(update_query, order_id)
                result =  {
                    "success": True,
                    "message": f"訂單 {order['order_number']} 已成功取消",
                    "cleaned_locks": 0,
                }
            else:
                cleaned_locks_count = await cleanup_all_order_locks(order_id, db)
                delete_query = "DELETE FROM daily_workforce_usage WHERE schedule_id IN (SELECT id FROM schedules WHERE order_id = $1)"
                await db.execute(delete_query, order_id)
                delete_query = "DELETE FROM schedules WHERE order_id = $1"
                await db.execute(delete_query, order_id)
                update_query = "UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = $1"
                await db.execute(update_query, order_id)
                result = {
                    "success": True,
                    "message": f"訂單 {order['order_number']} 已成功取消",
                    "cleaned_locks": cleaned_locks_count,
                }
            email_sent = False
            try:
                select_query = "SELECT u.email, u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.id = $1"
                user = await db.fetchrow(select_query, order_id)
                select_query = "SELECT preferred_date, preferred_time FROM booking_slots WHERE order_id = $1 ORDER BY is_selected DESC, is_primary DESC, preferred_date, preferred_time LIMIT 1"
                booking_slot = await db.fetchrow(select_query, order_id)
                if user:
                    order_data  = {
                    "order_id": order_id,
                    "order_number": order["order_number"],
                    "service_type": order["service_type"],
                    "location_address": order["location_address"],
                    "total_amount": order["total_amount"],
                    "preferred_date": booking_slot["preferred_date"] if booking_slot else None,
                    "preferred_time": booking_slot["preferred_time"] if booking_slot else None,
                    "user_email": user["email"],
                    "user_name": user["name"]
                }
                mail_result = send_cancellation_confirmation_email(order_data)
                email_sent = mail_result.get("success", False)
            except Exception as email_error:
                print(f"郵件發送失敗，但排程已成功: {email_error}")
            result["email_sent"] = email_sent
            return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"取消訂單失敗：{e}")
        raise HTTPException(status_code=500, detail="取消訂單失敗")
    

async def cleanup_all_order_locks(order_id: int, db):
    try:
        select_query = """
                SELECT DISTINCT 
                    tsl.id,
                    tsl.lock_type,
                    tsl.reference_id,
                    tsl.slot_date,
                    tsl.slot_time,
                    CASE 
                        WHEN tsl.reference_id IN (SELECT id FROM schedules WHERE order_id = $1) 
                        THEN 'schedule_lock'
                        WHEN tsl.id IN (SELECT temp_lock_id FROM booking_slots WHERE order_id = $1 AND temp_lock_id IS NOT NULL)
                        THEN 'booking_lock'
                        ELSE 'unknown'
                    END as lock_source
                FROM time_slot_locks tsl
                WHERE 
                    tsl.reference_id IN (
                        SELECT id FROM schedules WHERE order_id = $1
                    )
                    OR
                    tsl.id IN (
                        SELECT temp_lock_id 
                        FROM booking_slots 
                        WHERE order_id = $1 AND temp_lock_id IS NOT NULL
                    )
            """
        lock_records = await db.fetch(select_query, order_id)
        if not lock_records:
            print(f"訂單 {order_id} 沒有需要清理的鎖定記錄")
            return 0
        update_query = """
            UPDATE booking_slots 
            SET temp_lock_id = NULL, 
                is_locked = false, 
                lock_expires_at = NULL
            WHERE order_id = $1 AND temp_lock_id IS NOT NULL
        """
        await db.execute(update_query, order_id)
        lock_ids = [record["id"] for record in lock_records]
        if lock_ids:
            delete_query = "DELETE FROM time_slot_locks WHERE id = ANY($1)"
            delete_result = await db.execute(delete_query, lock_ids)
            deleted_count = 0
            if delete_result and "DELETE" in delete_result:
                deleted_count = int(delete_result.split()[1])
            print(f"成功刪除 {deleted_count} 個鎖定記錄")
            if deleted_count != len(lock_ids):
                print(f"警告：預期刪除 {len(lock_ids)} 個，實際刪除 {deleted_count} 個")
            return deleted_count
        return 0
    except Exception as e:
        print(f"清理訂單 {order_id} 鎖定時發生錯誤: {e}")
        return 0


async def upload_completion_file(order_id: int, file: UploadFile, db):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只允許上傳 PDF 檔案")
    if not file.size or file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="檔案大小不能超過 10MB")
    try:
        async with db.transaction():
            select_query = "SELECT id, order_number, status FROM orders WHERE id = $1 FOR UPDATE"
            order = await db.fetchrow(select_query, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            if order["status"] != "scheduled":
                raise HTTPException(
                    status_code=400, detail="只有已排程的訂單可以上傳完工報告"
                )
            s3_object_name = f"{order["order_number"]}_{uuid.uuid4().hex}_report.pdf"
            try:
                s3_client.upload_fileobj(
                    file.file,
                    S3_BUCKET_NAME,
                    s3_object_name,
                    ExtraArgs={
                        "ContentType": "application/pdf",
                        "ContentDisposition": f"inline; filename={file.filename}",
                    },
                )
            except ClientError as err:
                print(f"S3返回錯誤回應：{err}")
                raise HTTPException(
                    status_code=500, detail="S3返回錯誤回應，檔案上傳失敗"
                )
            file_url = f"{CLOUDFRONT_DOMAIN}/{s3_object_name}"
            select_query = (
                "SELECT completion_file_url FROM order_completions WHERE order_id = $1"
            )
            existing = await db.fetchrow(select_query, order_id)
            if existing:
                update_query = "UPDATE order_completions SET completion_file_url = $2, completion_file_name = $3 WHERE order_id = $1"
                await db.execute(update_query, order_id, file_url, file.filename)
                message = f"訂單 {order['order_number']} 驗收報告已更新"
            else:
                insert_query = "INSERT INTO order_completions(order_id, completion_file_url, completion_file_name) VALUES ($1, $2, $3)"
                await db.execute(insert_query, order_id, file_url, file.filename)
                message = f"訂單 {order['order_number']} 完工報告上傳成功"
            return {
                "success": True,
                "message": message,
                "completion_file_name": file.filename,
                "completion_file_url": file_url,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"上傳完工報告失敗: {e}")
        raise HTTPException(status_code=500, detail="上傳完工報告失敗")


async def update_order_completion_status(order_id: int, db):
    try:
        async with db.transaction():
            select_query = "SELECT id, order_number, status FROM orders WHERE id = $1 FOR UPDATE"
            order = await db.fetchrow(select_query, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            select_query = (
                "SELECT completion_file_url FROM order_completions WHERE order_id = $1"
            )
            existing = await db.fetchrow(select_query, order_id)
            if not existing:
                raise HTTPException(status_code=400, detail="請上傳驗收報告")
            update_query = "UPDATE orders SET status = 'completed', updated_at = NOW() WHERE id = $1"
            await db.execute(update_query, order_id)
            return {
                "success": True,
                "message": f"訂單 {order["order_number"]} 已完工",
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"更新完工狀態失敗：{e}")
        raise HTTPException(status_code=500, detail="更新完工狀態失敗")


async def get_completion_file(order_id: int, db):
    try:
        select_query = "SELECT id, order_number, status FROM orders WHERE id = $1"
        order = await db.fetchrow(select_query, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        select_query = "SELECT completion_file_url, completion_file_name FROM order_completions WHERE order_id = $1"
        report = await db.fetchrow(select_query, order_id)
        if not report:
            raise HTTPException(status_code=404, detail="該訂單尚未上傳完工報告")
        return {
            "order_id": order_id,
            "order_number": order["order_number"],
            "completion_file_url": report["completion_file_url"],
            "completion_file_name": report["completion_file_name"],
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"取得驗收報告失敗：{e}")
        raise HTTPException(status_code=500, detail="取得驗收報告失敗")
