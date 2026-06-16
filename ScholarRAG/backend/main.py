from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from rag import init, query_rag, clear_memory


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Starting init...")
        init()
        print("Init complete.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClearRequest(BaseModel):
    session_id: str


@app.post("/query")
async def query(
    question:   str                    = Form(...),
    session_id: str                    = Form("default"),
    file:       Optional[UploadFile]   = File(None),
):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    pdf_bytes = None
    if file and file.filename:
        pdf_bytes = await file.read()

    return query_rag(question, session_id, pdf_bytes)


@app.post("/clear")
def clear(req: ClearRequest):
    clear_memory(req.session_id)
    return {"status": "cleared"}


@app.get("/health")
def health():
    return {"status": "ok"}
