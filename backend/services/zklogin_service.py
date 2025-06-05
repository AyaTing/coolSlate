import os
import httpx
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

ENOKI_API_KEY = os.getenv("ENOKI_API_KEY")
ENOKI_API_BASE_URL = os.getenv("ENOKI_API_BASE_URL")
MYSTEN_PROVER_DEV_URL=os.getenv("MYSTEN_PROVER_DEV_URL")
MYSTEN_PROVER_URL=os.getenv("MYSTEN_PROVER_URL")


async def get_salt_and_address_from_enoki(jwt_token: str, client: httpx.AsyncClient):
    url = f"{ENOKI_API_BASE_URL}/zklogin"
    headers = {"Authorization": f"Bearer {ENOKI_API_KEY}", "zklogin-jwt": jwt_token}
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        if "data" not in result or not result["data"]:
            print("無法取得有效數據")
            raise HTTPException(status_code=502, detail="無法取得有效數據")
        return result["data"]
    except httpx.HTTPStatusError as e:
        print(f"與 ENOKI 連線出現錯誤：{e}")
        raise HTTPException(
            status_code=e.response.status_code, detail=f"連線出現錯誤：{e}"
        )
    except Exception as err:
        print(f"與 ENOKI 連線出現預期外錯誤：{err}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤")



async def get_zk_proof_from_mysten_prover(
    jwt_token: str,
    extended_public_key_str: str,
    max_epoch: int,
    randomness_str: str,
    user_salt: str,
    client: httpx.AsyncClient,
    key_claim_name: str = "sub"
):
    url = f"{MYSTEN_PROVER_DEV_URL}"
    headers = {
        "Content-Type": "application/json"}
    
    payload = {
        "jwt": jwt_token,
        "extendedEphemeralPublicKey": extended_public_key_str,
        "maxEpoch": max_epoch,
        "jwtRandomness": randomness_str,
        "salt": user_salt,
        "keyClaimName": key_claim_name
    }
    try:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result
    except httpx.HTTPStatusError as e:
        print(f"與 mysten prover 連線出現錯誤：{e}")
        raise HTTPException(
            status_code=e.response.status_code, detail=f"連線出現錯誤：{e}"
        )
    except Exception as err:
        print(f"與 mysten prover 連線出現預期外錯誤：{err}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤")
