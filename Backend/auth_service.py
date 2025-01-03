from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from db import execute_query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime
import bcrypt
import jwt
from typing import Optional
from datetime import timedelta

# Создание модели для данных пользователя
class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    birth_date: str = None  # Дата рождения в виде строки
    username: str
    password: str

# Создание модели для авторизации
class UserLogin(BaseModel):
    username: str
    password: str   

SECRET_KEY = "rip"  # Секретный ключ для JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Время действия токена

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (можно указать конкретные, например, ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешить все заголовки
)

# Функция для создания JWT токена
def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/register")
async def register_user(user: User):
    try:
        # Хэшируем пароль перед сохранением
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        birth_date = None
        if user.birth_date:
            birth_date = datetime.datetime.strptime(user.birth_date, '%Y-%m-%d').date()

        # SQL-запрос для регистрации пользователя
        query = """
        INSERT INTO public.users (first_name, last_name, email, birth_date, username, password)
        VALUES ($1, $2, $3, $4, $5, $6) 
        RETURNING id, first_name, last_name, email, birth_date, username;
        """
        values = (user.first_name, user.last_name, user.email, birth_date, user.username, hashed_password)

        # Выполнение запроса на добавление пользователя в базу данных
        result = await execute_query(query, values)

        if result:
            # Преобразование результата в словарь
            user_data = dict(result[0])  # Преобразуем Record в словарь
            # Убедимся, что birth_date сериализуем
            if user_data.get("birth_date"):
                user_data["birth_date"] = user_data["birth_date"].isoformat()
            
            return JSONResponse(
                content={"message": "User created successfully", "user": user_data},
                status_code=201
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to create user")
    except Exception as e:
        print(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/login")
async def login_user(credentials: UserLogin):
    try:
        query = """
        SELECT id, username, password FROM public.users WHERE username = $1
        """
        values = (credentials.username,)
        result = await execute_query(query, values)

        if not result:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = result[0]

        # Проверяем хэшированный пароль
        if not bcrypt.checkpw(credentials.password.encode('utf-8'), user["password"].encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Генерация JWT токена
        token = jwt.encode({"id": user["id"], "username": user["username"]}, SECRET_KEY, algorithm="HS256")

        return JSONResponse(
            content={"message": "Login successful", "token": token},
            status_code=200
        )
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
