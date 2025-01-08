import httpx
from fastapi import HTTPException
from typing import Any

async def verify_user(token: str) -> Any:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://127.0.0.1:8001/verify",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Проверка успешности ответа
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Если все прошло успешно, вернуть данные
        return response.json()
