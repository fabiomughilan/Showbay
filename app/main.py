from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import SummaryCreate, SummaryOut, SummaryUpdate
from app.models import Summary
from app.crud import get_summary
from app.groq_client import GroqClient
from app.exceptions import ExternalServiceError
from contextlib import asynccontextmanager
from app.db import engine
from app.models import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Groq Summarizer",
    description="AI-powered text summarizer using Groq Llama 3. Submit long text to receive concise summaries.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "status": "ok",
        "message": "Groq Summarizer API. Visit /docs for interactive API documentation."
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.exception_handler(ExternalServiceError)
async def external_service_handler(request, exc: ExternalServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request, exc: SQLAlchemyError):
    logging.exception("Database error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal database error"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

client = GroqClient()

@app.post("/summaries", response_model=SummaryOut, status_code=201)
async def create_summary(data: SummaryCreate, db: AsyncSession = Depends(get_db)):
    try:
        summary_text = await client.summarize(data.input_text)
    except Exception:
        # In a real app we might log the exception info here
        raise ExternalServiceError()

    obj = Summary(
        input_text=data.input_text,
        summary_text=summary_text,
        model="groq"
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

@app.get("/summaries/{id}", response_model=SummaryOut)
async def read_summary(id: str, db: AsyncSession = Depends(get_db)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(404, detail="Summary not found")
    return obj

@app.put("/summaries/{id}", response_model=SummaryOut)
async def update_summary(id: str, data: SummaryUpdate, db: AsyncSession = Depends(get_db)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(404, detail="Summary not found")
    obj.summary_text = data.summary_text
    await db.commit()
    await db.refresh(obj) # Refresh to get updated timestamp if needed/ensure validity
    return obj

@app.delete("/summaries/{id}", status_code=204)
async def delete_summary(id: str, db: AsyncSession = Depends(get_db)):
    obj = await get_summary(db, id)
    if not obj:
        raise HTTPException(404, detail="Summary not found")
    await db.delete(obj)
    await db.commit()
