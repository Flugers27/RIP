import asyncpg
from fastapi import HTTPException

# Функция для выполнения SQL-запроса в PostgreSQL
async def execute_query(query: str, values: tuple):
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(user='postgres', password='admin', database='rip', host='localhost')
        
        # Выполнение запроса
        result = await conn.fetch(query, *values)
        
        # Закрытие соединения с базой данных
        await conn.close()
        
        return result
    except Exception as e:
        print(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Database query failed")
