from fastapi import FastAPI, File, UploadFile
import shutil
import os

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Загрузка файла
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": file_path}

# Получить список загруженных файлов
@app.get("/files/")
def list_files():
    files = os.listdir(UPLOAD_DIR)
    return {"files": files}

# Удалить файл
@app.delete("/files/{filename}")
def delete_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"detail": f"{filename} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")
