from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from shared.db import db  # Используем обновленный db.py с пулом соединений
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import bcrypt
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

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/register")
async def register_user(user: User):
    try:
        # Проверяем уникальность email и username
        check_query = "SELECT id FROM public.users WHERE email = $1 OR username = $2"
        existing_user = await db.execute_query(check_query, (user.email, user.username))
        if existing_user:
            raise HTTPException(status_code=400, detail="Email or username already exists")

        # Хэшируем пароль перед сохранением
        hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Преобразование даты рождения в формат даты
        birth_date = None
        if user.birth_date:
            birth_date = datetime.strptime(user.birth_date, "%Y-%m-%d").date()

        # SQL-запрос для добавления пользователя
        query = """
        INSERT INTO public.users (first_name, last_name, email, birth_date, username, password)
        VALUES ($1, $2, $3, $4, $5, $6) 
        RETURNING id, first_name, last_name, email, birth_date, username;
        """
        values = (user.first_name, user.last_name, user.email, birth_date, user.username, hashed_password)

        result = await db.execute_query(query, values)
        user_data = dict(result[0])

        # Форматируем дату рождения для вывода
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


@app.post("/login")
async def login_user(credentials: UserLogin):
    try:
        query = "SELECT id, username, password FROM public.users WHERE username = $1"
        result = await db.execute_query(query, (credentials.username,))

        if not result:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        user = result[0]

        # Проверяем хэшированный пароль
        if not bcrypt.checkpw(credentials.password.encode("utf-8"), user["password"].encode("utf-8")):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        # Генерация JWT токена
        token = create_access_token({"id": user["id"], "username": user["username"]})

        return JSONResponse(
            content={"message": "Login successful", "token": token}, status_code=200
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
