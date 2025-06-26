import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


async def get_coordinates(address: str, client: httpx.AsyncClient):
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY, "language": "zh-TW"}
    try:
        response = await client.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
        else:
            print(f"地址解析失敗: {address}, 原因: {data['status']}")
            return None
    except httpx.HTTPStatusError as e:
        print(f"Google Maps API 請求失敗: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"解析地址時發生未知錯誤: {e}")
        return None
