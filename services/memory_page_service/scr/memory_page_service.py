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
class BiographyHeading(BaseModel):
    id_heading: int
    order_heading: int
    name_heading: str
    content: str


# Модель для мемориальной страницы
class MemorialPage(BaseModel):
    first_name: str
    middle_name: str = None
    last_name: str
    birth_date: str
    death_date: str
    biography: list[BiographyHeading] = [BiographyHeading]
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

# Функция проверки изменения зоголовков
def get_chek_action(page_id: int, page: MemorialPage):

    if page.biography == []:
        query = """
        SELECT id_heading,  'delete' AS action 
        FROM public.headlines_biography
        WHERE id_memory_page = $1 
        """
        values = (page_id,)

        return (query,values,{})
    
    else:

        bio_dict = {'id_heading' : [],
                'id_heading_str_list' : [],
                'id_heading_str_data' : [],
                'order_heading' : [],
                'name_heading' : [],
                'content' : []}
        

        for head in page.biography:
            bio_dict['id_heading'].append(head.id_heading)
            bio_dict['order_heading'].append(head.order_heading)
            bio_dict['name_heading'].append(head.name_heading)
            bio_dict['content'].append(head.content)

            bio_dict['id_heading_str_list'].append(str(head.id_heading))
            bio_dict['id_heading_str_data'].append('(' + str(head.id_heading) + ')')


        bio_dict['id_heading_str_list'] = ", ".join(bio_dict['id_heading_str_list'])
        bio_dict['id_heading_str_data'] = ", ".join(bio_dict['id_heading_str_data'])

        query = """
        SELECT id_heading,  'delete' AS action 
        FROM public.headlines_biography
        WHERE id_memory_page = $1 AND (id_heading not in ("""+ bio_dict['id_heading_str_list'] +"""))

        UNION 
        SELECT arr.id_heading, 'insert' AS action 
        FROM (values """+ bio_dict['id_heading_str_data'] +""" ) AS arr(id_heading)
        LEFT JOIN public.headlines_biography AS hb 
        ON hb.id_heading = arr.id_heading
        WHERE hb.id_heading IS NULL

        UNION 
        SELECT id_heading,  'update' AS action 
        FROM public.headlines_biography
        WHERE id_memory_page = $1 AND (id_heading in ("""+ bio_dict['id_heading_str_list'] +"""))
        ORDER BY id_heading;
        """
        values = (page_id,)

        return (query,values,bio_dict)



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
        INSERT INTO memory_pages_human (first_name, middle_name, last_name, birth_date, death_date, public, user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id_memory_page, first_name, middle_name, last_name, birth_date, death_date, public;
        """
        values = (page.first_name, page.middle_name, page.last_name, birth_date, death_date, page.public, user_id)
        result_page = await db.execute_query(query, values)

        result = dict(result_page[0])
        result["biography"] = []

        for row in page.biography:
            if row is not None:
                query = """
                INSERT INTO headlines_biography (name_heading, order_heading, content, id_memory_page)
                VALUES ($1, $2, $3, $4)
                RETURNING id_heading, name_heading, order_heading, content, id_memory_page;
                """
                values = (row.name_heading, row.order_heading, row.content, dict(result_page[0])['id_memory_page'])

                result_head = await db.execute_query(query, values)
                result["biography"].append(dict(result_head[0]))

        if result:
            return {"message": "Memorial page created successfully", "page": result}
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
        SELECT mph.id_memory_page, mph.first_name, mph.middle_name, mph.last_name, mph.birth_date, mph.death_date, mph.public,
            hb.id_heading, hb.name_heading, hb.order_heading, hb.content
        FROM memory_pages_human AS mph
        INNER JOIN headlines_biography AS hb ON hb.id_memory_page = mph.id_memory_page
        WHERE mph.id_memory_page = $1 AND mph.public = TRUE
        ORDER BY hb.order_heading;
        """
        values = (page_id,)
        result = await db.execute_query(query, values)

        if not result:
            raise HTTPException(status_code=404, detail="Public memorial page not found")
        
        # Построение структуры JSON
        page_data = None
        biography = []

        for row in result:
            if page_data is None:
                # Основная информация о странице памяти
                page_data = {
                    "first_name": row["first_name"],
                    "middle_name": row["middle_name"],
                    "last_name": row["last_name"],
                    "birth_date": row["birth_date"],
                    "death_date": row["death_date"],
                    "public": row["public"],
                    "biography": []
                }
            
            # Добавляем биографические заголовки (если есть)
            if row["id_heading"] is not None:
                biography.append({
                    "order_heading": row["order_heading"],
                    "name_heading": row["name_heading"],
                    "content": row["content"]
                })
        
        # Добавляем биографию в структуру
        page_data["biography"] = biography

        return {"page": page_data}
    
    except Exception as e:
        print(f"Error fetching public memorial page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Получить мемориальную страницу, созданную текущим пользователем
@app.get("/memorial_page/user/{page_id}")
async def get_user_memorial_page(page_id: int, user_id: int = Depends(get_current_user)):

    try:
        query = """
        SELECT mph.id_memory_page, mph.first_name, mph.middle_name, mph.last_name, mph.birth_date, mph.death_date, mph.public,
            hb.id_heading, hb.name_heading, hb.order_heading, hb.content
        FROM memory_pages_human AS mph
        INNER JOIN headlines_biography AS hb ON hb.id_memory_page = mph.id_memory_page
        WHERE mph.id_memory_page = $1 AND mph.user_id = $2
        ORDER BY hb.order_heading;
        """
        values = (page_id, user_id)
        result = await db.execute_query(query, values)


        if not result:
            raise HTTPException(status_code=404, detail="User's memorial page not found")
        
        # Построение структуры JSON
        page_data = None
        biography = []

        for row in result:
            if page_data is None:
                # Основная информация о странице памяти
                page_data = {
                    "first_name": row["first_name"],
                    "middle_name": row["middle_name"],
                    "last_name": row["last_name"],
                    "birth_date": row["birth_date"],
                    "death_date": row["death_date"],
                    "public": row["public"],
                    "biography": []
                }
            
            # Добавляем биографические заголовки (если есть)
            if row["id_heading"] is not None:
                biography.append({
                    "order_heading": row["order_heading"],
                    "name_heading": row["name_heading"],
                    "content": row["content"]
                })
        
        # Добавляем биографию в структуру
        page_data["biography"] = biography

        return {"page": page_data}

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
        SET first_name = $1, middle_name = $2, last_name = $3, birth_date = $4, death_date = $5, public = $6
        WHERE id_memory_page = $7 AND user_id = $8
        RETURNING id_memory_page, first_name, middle_name, last_name, birth_date, death_date, public;
        """
        values = (
            page.first_name,
            page.middle_name,
            page.last_name,
            birth_date,
            death_date,
            page.public,
            page_id,
            user_id,
        )
        
        result_page = await db.execute_query(query, values)
        result = dict(result_page[0])
        result["biography"] = []

        if not result_page:
            raise HTTPException(status_code=404, detail="User's memorial page not found")
        
        # ВЫВОД ТАБЛИЦЫ ДЕЙСТВИЙ ДЛЯ ЗАГОЛОВКА
        query, values, bio_dict = get_chek_action(page_id, page)

        print("dsg")

        if query is not None:
            result_chek_action = await db.execute_query(query, values)

            # print(result_chek_action)
            for  head in result_chek_action:
                head = dict(head)
                
                # UPDATE
                if head["action"] == "update":
                    # print("update")
                    index =  bio_dict['id_heading'].index(head["id_heading"])

                    query = """
                    UPDATE headlines_biography
                    SET order_heading = $1, name_heading = $2, content = $3
                    WHERE id_heading = $4 AND id_memory_page = $5
                    RETURNING id_heading, order_heading, name_heading, content, id_memory_page;
                    """
                    values = (
                        bio_dict['order_heading'][index],
                        bio_dict['name_heading'][index],
                        bio_dict['content'][index],
                        head["id_heading"],
                        page_id,
                    )
                    
                    result_action = await db.execute_query(query, values)
                    result_action = dict(result_action[0])
                    result_action['action'] = "update"

                    result["biography"].append(result_action)
                    #print(result_action)
                
                # DELETE
                elif head["action"] == "delete":
                    # print("delete")

                    query = """
                    DELETE FROM headlines_biography 
                    WHERE id_memory_page = $1 AND id_heading = $2 
                    RETURNING id_heading;
                    """
                    values = (page_id, head["id_heading"])

                    result_action = await db.execute_query(query, values)
                    result_action = dict(result_action[0])
                    result_action['action'] = "delete"

                    result["biography"].append(result_action)
                    #print(result_action)

                # INSERT
                elif head["action"]== "insert":
                    # print("insert")
                    index =  bio_dict['id_heading'].index(head["id_heading"])

                    query = """
                    INSERT INTO headlines_biography (order_heading, name_heading, content, id_memory_page)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id_heading, order_heading, name_heading, content, id_memory_page;
                    """
                    values = (
                        bio_dict['order_heading'][index],
                        bio_dict['name_heading'][index],
                        bio_dict['content'][index],
                        page_id,)
                    
                    result_action = await db.execute_query(query, values)
                    result_action = dict(result_action[0])
                    result_action['action'] = "insert"

                    result["biography"].append(result_action)
                    #print(result_action)

                if not result_action:
                    raise HTTPException(status_code=404, detail="Headers memorial page not found")

        if result:
            return {"message": "Memorial page updated successfully", "page": result}
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
