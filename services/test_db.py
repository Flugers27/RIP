import asyncpg
import asyncio

async def get_all_users():
    try:
        # Подключение к базе данных
        conn = await asyncpg.connect(user='postgres', password='admin', database='rip', host='localhost')
        
        # Запрос к базе данных, указание схемы public
        query = "SELECT * FROM public.users ;"
        
        # Выполнение запроса
        result = await conn.fetch(query)
        
        # Вывод результатов
        print("Users in database:")
        for user in result:
            print(user)  # Каждая запись будет отображена в виде словаря

        # Закрытие соединения с базой данных
        await conn.close()

    except Exception as e:
        print(f"Error during database query: {e}")

# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(get_all_users())
