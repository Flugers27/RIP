import asyncpg
from fastapi import HTTPException

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)
            print("Database connection pool created successfully.")
        except Exception as e:
            print(f"Error creating database connection pool: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to the database")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("Database connection pool closed.")

    async def execute_query(self, query: str, values: tuple = ()):
        if not self.pool:
            raise HTTPException(status_code=500, detail="Database connection pool is not initialized")

        try:
            async with self.pool.acquire() as conn:
                return await conn.fetch(query, *values)
        except Exception as e:
            print(f"Database query error: {e}")
            raise HTTPException(status_code=500, detail="Database query failed")


# Экземпляр базы данных с DSN
db = Database(dsn="postgresql://postgres:admin@localhost/rip")
