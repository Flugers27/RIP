from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, ValidationError, model_validator
from shared.db import db
from fastapi.middleware.cors import CORSMiddleware
import jwt
import sys
import os

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

SECRET_KEY = "rip"
ALGORITHM = "HS256"

app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель для мемориальной страницы
class MemorialPage(BaseModel):
    first_name: str
    middle_name: str = None
    last_name: str
    birth_date: str
    death_date: str
    biography: str = None
    public: bool

    @model_validator(mode="after")
    def validate_dates(cls, values):
        birth_date = datetime.strptime(values.birth_date, "%Y-%m-%d").date()
        death_date = datetime.strptime(values.death_date, "%Y-%m-%d").date()

        if death_date < birth_date:
            raise ValueError("Дата смерти раньше даты рождения")
        return values

# Функция для извлечения токена из cookies и проверки авторизации
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["id_user"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Функция для преобразования строки в объект date
def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format for '{date_str}'. Use YYYY-MM-DD.",
        )

@app.on_event("startup")
async def startup():
    await db.connect()  # Инициализация подключения к базе данных

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()  # Закрытие соединения при завершении приложения

# Создать мемориальную страницу
@app.post("/memorial_page/create", status_code=201)
async def create_memorial_page(page: MemorialPage, user_id: int = Depends(get_current_user)):
    try:
        # Преобразование строковых дат в объекты типа date
        birth_date = parse_date(page.birth_date)
        death_date = parse_date(page.death_date)

        # Проверка: дата смерти должна быть позже даты рождения
        if death_date < birth_date:
            raise HTTPException(status_code=400, detail="Дата смерти раньше даты рождения")
        
        query = """
        INSERT INTO memory_pages_human (first_name, middle_name, last_name, birth_date, death_date, biography, public, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id_memory_page, first_name, middle_name, last_name, birth_date, death_date, biography, public;
        """
        values = (page.first_name, page.middle_name, page.last_name, birth_date, death_date, page.biography, page.public, user_id)
        result = await db.execute_query(query, values)

        if result:
            return {"message": "Memorial page created successfully", "page": dict(result[0])}
        else:
            raise HTTPException(status_code=400, detail="Failed to create memorial page")
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error creating memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Вывести список страниц памяти только публичные
@app.get("/memorial_pages/public")
async def get_public_memorial_pages():
    try:
        query = """
        SELECT id_memory_page, first_name, middle_name, last_name, birth_date, death_date
        FROM memory_pages_human
        WHERE public = TRUE
        ORDER BY id_memory_page;;
        """
        result = await db.execute_query(query)

        if result:
            return {"pages": [dict(row) for row in result]}
        else:
            return {"pages": []}  # Пустой список, если публичных страниц нет
    except Exception as e:
        print(f"Error fetching public memorial pages: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Вывести список страниц памяти, созданных пользователем
@app.get("/memorial_pages/user")
async def get_user_memorial_pages(user_id: int = Depends(get_current_user)):
    try:
        query = """
        SELECT id_memory_page, first_name, middle_name, last_name, birth_date, death_date, public
        FROM memory_pages_human
        WHERE user_id = $1
        ORDER BY id_memory_page;
        """
        values = (user_id,)
        result = await db.execute_query(query, values)

        if result:
            return {"pages": [dict(row) for row in result]}
        else:
            return {"pages": []}  # Пустой список, если у пользователя нет созданных страниц
    except Exception as e:
        print(f"Error fetching user's memorial pages: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Получить публичную мемориальную страницу
@app.get("/memorial_page/public/{page_id}")
async def get_public_memorial_page(page_id: int):
    """
    Эндпоинт возвращает публичную мемориальную страницу по её ID.
    """
    try:
        query = """
        SELECT id_memory_page, first_name, middle_name, last_name, birth_date, death_date, biography, public
        FROM memory_pages_human
        WHERE id_memory_page = $1 AND public = TRUE;
        """
        values = (page_id,)
        result = await db.execute_query(query, values)

        if result:
            return {"page": dict(result[0])}
        else:
            raise HTTPException(status_code=404, detail="Public memorial page not found")
    except Exception as e:
        print(f"Error fetching public memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Получить мемориальную страницу, созданную текущим пользователем
@app.get("/memorial_page/user/{page_id}")
async def get_user_memorial_page(page_id: int, user_id: int = Depends(get_current_user)):
    """
    Эндпоинт возвращает мемориальную страницу, созданную текущим пользователем, по её ID.
    """
    try:
        query = """
        SELECT id_memory_page, first_name, middle_name, last_name, birth_date, death_date, biography, public
        FROM memory_pages_human
        WHERE id_memory_page = $1 AND user_id = $2;
        """
        values = (page_id, user_id)
        result = await db.execute_query(query, values)

        if result:
            return {"page": dict(result[0])}
        else:
            raise HTTPException(status_code=404, detail="User's memorial page not found")
    except Exception as e:
        print(f"Error fetching user's memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Обновить мемориальную страницу
@app.put("/memorial_page/edit/{page_id}")
async def update_memorial_page(page_id: int, page: MemorialPage, user_id: int = Depends(get_current_user)):
    try:
        # Преобразование строковых дат в объекты типа date
        birth_date = parse_date(page.birth_date)
        death_date = parse_date(page.death_date)

        query = """
        UPDATE memory_pages_human
        SET first_name = $1, middle_name = $2, last_name = $3, birth_date = $4, death_date = $5, biography = $6, public = $7
        WHERE id_memory_page = $8 AND user_id = $9
        RETURNING id_memory_page, first_name, middle_name, last_name, birth_date, death_date, biography, public;
        """
        values = (
            page.first_name,
            page.middle_name,
            page.last_name,
            birth_date,
            death_date,
            page.biography,
            page.public,
            page_id,
            user_id,
        )
        result = await db.execute_query(query, values)

        if result:
            return {"message": "Memorial page updated successfully", "page": dict(result[0])}
        else:
            raise HTTPException(status_code=404, detail="Memorial page not found or unauthorized")
    except Exception as e:
        print(f"Error updating memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Удалить мемориальную страницу
@app.delete("/memorial_page/delete/{page_id}")
async def delete_memorial_page(page_id: int, user_id: int = Depends(get_current_user)):
    try:
        query = """
        DELETE FROM memory_pages_human WHERE id_memory_page = $1 AND user_id = $2 RETURNING id_memory_page;
        """
        values = (page_id, user_id)
        result = await db.execute_query(query, values)

        if result:
            return {"message": "Memorial page deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Memorial page not found or unauthorized")
    except Exception as e:
        print(f"Error deleting memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
