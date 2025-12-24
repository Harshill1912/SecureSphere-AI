from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import asyncio

from engine import ask_question, ingest_pdf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"message": "SecureSphere backend running"}

class ChatRequest(BaseModel):
    query: str
    filename: str

@app.post("/chat")
async def chat(req: ChatRequest):
    clean_filename = os.path.basename(req.filename).lower()

    answer = await asyncio.to_thread(
        ask_question,
        req.query,
        clean_filename
    )

    return {"answer": answer}

@app.post("/upload")
def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    if os.path.exists(file_path):
        return {
            "message": "PDF already uploaded",
            "file": file.filename
        }

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = ingest_pdf(file_path)

    return {
        "message": "PDF uploaded & indexed successfully",
        "file": result["file"],
        "chunks_added": result["chunks"]
    }
