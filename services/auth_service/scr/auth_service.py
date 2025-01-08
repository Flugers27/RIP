from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from shared.db import db
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import traceback
import bcrypt
import jwt
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Создание модели для данных пользователя при регистрации
class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str = None  # Дата рождения в виде строки
    user_name: str
    password: str  # Новый пароль


class UserLogin(BaseModel):
    user_name: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


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


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


# === Функция для получения текущего пользователя из токена (из куки) ===
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")  # Извлекаем токен из куки
    if not token:
        raise HTTPException(status_code=401, detail="Access token is missing")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id_user = payload.get("id_user")
        if id_user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id_user": id_user, "user_name": payload.get("user_name")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# === РЕГИСТРАЦИЯ ===
@app.post("/register")
async def register_user(user: User):
    try:
        # Проверка наличия пользователя с таким же email или user_name
        check_query = "SELECT id_user FROM public.users WHERE email = $1 OR user_name = $2"
        existing_user = await db.execute_query(check_query, (user.email, user.user_name))
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or user_name already exists")

        # Хэширование пароля
        hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Обработка даты рождения, если она указана
        birth_date = None
        if user.birth_date:
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()

        # Запрос на добавление нового пользователя в базу
        query = """
        INSERT INTO public.users (first_name, last_name, email, birth_date, user_name, password)
        VALUES ($1, $2, $3, $4, $5, $6) 
        RETURNING id_user, first_name, last_name, email, birth_date, user_name;
        """
        values = (user.first_name, user.last_name, user.email, birth_date, user.user_name, hashed_password)

        result = await db.execute_query(query, values)
        user_data = dict(result[0])

        # Форматирование даты рождения в ISO-формат, если она указана
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


# === АВТОРИЗАЦИЯ ===
@app.post("/login")
async def login_user(credentials: UserLogin):
    try:
        query = "SELECT id_user, user_name, password FROM public.users WHERE user_name = $1"
        result = await db.execute_query(query, (credentials.user_name,))

        if not result:
            raise HTTPException(status_code=401, detail="Invalid user_name or password")

        user = result[0]

        if not bcrypt.checkpw(credentials.password.encode("utf-8"), user["password"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid user_name or password")

        token = create_access_token({"id_user": user["id_user"], "user_name": user["user_name"]})

        response = JSONResponse(
            content={"message": "Login successful"}, status_code=200
        )
        response.set_cookie(key="access_token", value=token, httponly=True)  # Устанавливаем токен как HTTP-only cookie
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
