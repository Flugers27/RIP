from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

# Список микросервисов и их адресов
MICROSERVICES = {
    "auth": "http://localhost:8001",
    "profile": "http://localhost:8002",
    "memorial": "http://localhost:8003",
}

# Маршрутизация запросов
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request):
    if service not in MICROSERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    # Формируем URL микросервиса
    url = f"{MICROSERVICES[service]}/{path}"

    # Переносим данные из запроса клиента
    method = request.method
    headers = request.headers
    body = await request.body()

    # Отправляем запрос на микросервис
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, content=body)

    # Возвращаем ответ клиента
    return response.json()

@app.get("/")
def home():
    return {"message": "API Gateway is running"}
