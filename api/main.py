import os
from typing import Dict, Any, Optional
from dataclasses import asdict
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.ocr.engine import PillTwinOCR
from src.matching.engine import PillTwinEngine

app = FastAPI(
    title="PillTwin API",
    description="Find your medicine's generic twin (PMBJP Jan Aushadhi equivalent) with transparent data-driven savings.",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import psutil
import asyncio

# Global engines initialized once at startup (Rule 1 & Render 512MB requirement)
engine = PillTwinEngine()
ocr_system = PillTwinOCR(brand_matcher=engine.brand_matcher)

# Global lock: process strictly ONE OCR request at a time (Render 512MB requirement)
ocr_lock = asyncio.Lock()
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB cap

# Measure and state startup memory
_process = psutil.Process(os.getpid())
STARTUP_MEMORY_MB = round(_process.memory_info().rss / (1024 * 1024), 2)
print(f"[PillTwin Startup] Data and OCR loaded once. Memory: {STARTUP_MEMORY_MB} MB (Engine: {ocr_system.engine_name})")

MANDATORY_DISCLAIMER = "Information only, not medical advice. Ask your doctor or pharmacist before changing any medicine."

@app.get("/health")
@app.get("/api/health")
async def health():
    curr_mem = round(_process.memory_info().rss / (1024 * 1024), 2)
    return {
        "status": "healthy",
        "ocr_engine": ocr_system.engine_name,
        "total_generics_indexed": len(engine.formulary),
        "startup_memory_mb": STARTUP_MEMORY_MB,
        "current_memory_mb": curr_mem
    }

@app.get("/api/data-info")
async def get_data_info():
    """
    Data provenance and pricing metadata.
    Enforces Rule 2 (two separate dates, unstated effective date source, indicative data age note).
    """
    return {
        "price_list_export_date": "2026-11-07",
        "price_list_date": "2026-11-07",
        "price_list_date_source": "PDF creation date; official effective date not stated",
        "data_download_date": "2026-11-19",
        "data_age_note": "brand prices may be outdated (~2 years old) and savings are indicative",
        "dataset_origin": "JuniorAlive/Indian-Medicine-Dataset (commit d584adf)",
        "dataset_licence": "MIT License",
        "pmbjp_source": "Pradhan Mantri Bhartiya Janaushadhi Pariyojana official product list PDF",
        "disclaimer": MANDATORY_DISCLAIMER
    }

@app.post("/api/scan")
@app.post("/api/ocr/scan")
async def scan_strip(file: UploadFile = File(...)):
    """
    Processes medicine packaging photo strictly in memory (Rule 6).
    Enforces 5 MB upload size limit and 1600 px long side cap.
    Processes one OCR request at a time using ocr_lock.
    Returns raw OCR text and candidate brand suggestions (Rule 4).
    NEVER produces an exact match by itself.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image bytes cannot be empty.")

    if len(image_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded image ({len(image_bytes)/(1024*1024):.2f} MB) exceeds maximum allowed size of 5 MB."
        )

    # Process strictly in memory (zero disk writes, EXIF stripped immediately, 1 request at a time)
    async with ocr_lock:
        try:
            ocr_res = ocr_system.scan_strip_photo(image_bytes)
        finally:
            del image_bytes
            import gc
            gc.collect()

    response = JSONResponse(content={
        "engine_name": ocr_res.engine_name,
        "raw_ocr_text": ocr_res.raw_ocr_text,
        "cleaned_candidate_lines": ocr_res.cleaned_candidate_lines,
        "extracted_strengths": ocr_res.extracted_strengths,
        "extracted_cues": ocr_res.extracted_cues,
        "suggested_brands": ocr_res.suggested_brands,
        "low_confidence": ocr_res.low_confidence,
        "low_confidence_message": ocr_res.low_confidence_message,
        "exact_match_produced": False,
        "prompt_message": ocr_res.prompt_message,
        "disclaimer": ocr_res.disclaimer
    })

    # Strict Rule 6: No caching of sensitive health photos
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response

@app.post("/api/match")
async def match_medicine(payload: Dict[str, Any]):
    """
    Matches a user-confirmed brand name against PMBJP formulary index.
    Executes Rule 1 (active salts, strengths, form, release) and Rule 2 (prices & dates).
    """
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")

    result = engine.match_item(query)
    return JSONResponse(content=asdict(result))

# Serve static frontend UI if available
ui_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
if os.path.exists(ui_dir):
    app.mount("/static", StaticFiles(directory=ui_dir), name="static")

    @app.get("/")
    async def serve_index():
        index_path = os.path.join(ui_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(
                index_path,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        return {"message": "PillTwin API is running. UI index.html not yet built."}
