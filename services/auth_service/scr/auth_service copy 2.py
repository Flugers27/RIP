from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from shared.db import db  # Используем обновленный db.py с пулом соединений
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer  # Импортируем для извлечения токена
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import SecurityScheme
from datetime import datetime, timedelta
from fastapi.openapi.utils import get_openapi
import bcrypt
import jwt
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Создание моделей для данных пользователя
class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str = None  # Дата рождения в виде строки
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


# Константы
SECRET_KEY = "rip"  # Секретный ключ для JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Время действия токена

app = FastAPI()

# Функция для создания JWT токена
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Создаем объект для извлечения токена из заголовка
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Настройка кастомной схемы OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Ваше API",
        version="1.0.0",
        description="Описание вашего API",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/login",
                }
            },
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            security = method.get("security", [])
            security.append({"OAuth2PasswordBearer": []})
            method["security"] = security
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

# ===Функция для получения текущего пользователя из токена===
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": user_id, "username": payload.get("username")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ===РЕГИСТРАЦИЯ===
@app.post("/register") 
async def register_user(user: User):
    try:
        check_query = "SELECT id FROM public.users WHERE email = $1 OR username = $2"
        existing_user = await db.execute_query(check_query, (user.email, user.username))
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or username already exists")

        hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        birth_date = None
        if user.birth_date:
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()

        query = """
        INSERT INTO public.users (first_name, last_name, email, birth_date, username, password)
        VALUES ($1, $2, $3, $4, $5, $6) 
        RETURNING id, first_name, last_name, email, birth_date, username;
        """
        values = (user.first_name, user.last_name, user.email, birth_date, user.username, hashed_password)

        result = await db.execute_query(query, values)
        user_data = dict(result[0])

        if user_data.get("birth_date"):
            user_data["birth_date"] = user_data["birth_date"].isoformat()

        return JSONResponse(
            content={"message": "User created successfully", "user": user_data}, status_code=201
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ===АВТОРИЗАЦИЯ===
@app.post("/login")
async def login_user(credentials: UserLogin):
    try:
        query = "SELECT id, username, password FROM public.users WHERE username = $1"
        result = await db.execute_query(query, (credentials.username,))

        if not result:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = result[0]

        if not bcrypt.checkpw(credentials.password.encode("utf-8"), user["password"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_access_token({"id": user["id"], "username": user["username"]})

        return JSONResponse(
            content={"message": "Login successful", "token": token}, status_code=200
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ===ПОКАЗАТЬ ИНФОРМАЦИЮ О ПОЛЬЗОВАТЕЛЕ (GET)===
@app.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        query = "SELECT id, first_name, last_name, email, birth_date, username FROM public.users WHERE id = $1"
        result = await db.execute_query(query, (user_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = dict(result[0])
        
        if user_data.get("birth_date"):
            user_data["birth_date"] = user_data["birth_date"].isoformat()

        return JSONResponse(content={"user": user_data}, status_code=200)
    except Exception as e:
        print(f"Error during fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# ===ОБНОВИТЬ ИНФОРМАЦИЮ О ПОЛЬЗОВАТЕЛЕ (PUT)===
@app.put("/profile")
async def update_profile(user: User, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]
        
        check_query = "SELECT id FROM public.users WHERE (email = $1 OR username = $2) AND id != $3"
        existing_user = await db.execute_query(check_query, (user.email, user.username, user_id))
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or username already exists")

        hashed_password = user.password
        if user.password:
            hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        birth_date = None
        if user.birth_date:
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()

        query = """
        UPDATE public.users 
        SET first_name = $1, last_name = $2, email = $3, birth_date = $4, username = $5, password = $6
        WHERE id = $7 
        RETURNING id, first_name, last_name, email, birth_date, username;
        """
        values = (user.first_name, user.last_name, user.email, birth_date, user.username, hashed_password, user_id)

        result = await db.execute_query(query, values)
        updated_user = dict(result[0])

        if updated_user.get("birth_date"):
            updated_user["birth_date"] = updated_user["birth_date"].isoformat()

        return JSONResponse(
            content={"message": "Profile updated successfully", "user": updated_user}, status_code=200
        )
    except Exception as e:
        print(f"Error during updating profile: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    



    
