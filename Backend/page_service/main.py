from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Модель страницы памяти
class MemoryPage(BaseModel):
    id: int
    title: str
    description: str
    is_public: bool

# Имитация базы данных
memory_pages = []

# Создать новую страницу
@app.post("/pages/", response_model=MemoryPage)
def create_page(page: MemoryPage):
    memory_pages.append(page)
    return page

# Получить все страницы (публичные и приватные)
@app.get("/pages/", response_model=List[MemoryPage])
def get_pages():
    return memory_pages

# Получить страницу по ID
@app.get("/pages/{page_id}", response_model=MemoryPage)
def get_page(page_id: int):
    for page in memory_pages:
        if page.id == page_id:
            return page
    raise HTTPException(status_code=404, detail="Page not found")

# Обновить страницу
@app.put("/pages/{page_id}", response_model=MemoryPage)
def update_page(page_id: int, updated_page: MemoryPage):
    for i, page in enumerate(memory_pages):
        if page.id == page_id:
            memory_pages[i] = updated_page
            return updated_page
    raise HTTPException(status_code=404, detail="Page not found")

# Удалить страницу
@app.delete("/pages/{page_id}")
def delete_page(page_id: int):
    global memory_pages
    memory_pages = [page for page in memory_pages if page.id != page_id]
    return {"detail": "Page deleted"}
