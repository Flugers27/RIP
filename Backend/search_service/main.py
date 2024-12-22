from fastapi import FastAPI, HTTPException
from typing import List
from pydantic import BaseModel

app = FastAPI()

# Имитация базы данных для страниц
class MemoryPage(BaseModel):
    id: int
    title: str
    description: str
    is_public: bool

memory_pages = [
    {"id": 1, "title": "In Memory of John", "description": "A beloved father.", "is_public": True},
    {"id": 2, "title": "Remembering Alice", "description": "A kind soul and teacher.", "is_public": True},
]

# Поиск страниц
@app.get("/search/", response_model=List[MemoryPage])
def search_pages(query: str):
    results = [
        page for page in memory_pages
        if query.lower() in page["title"].lower() or query.lower() in page["description"].lower()
    ]
    if not results:
        raise HTTPException(status_code=404, detail="No pages found")
    return results

