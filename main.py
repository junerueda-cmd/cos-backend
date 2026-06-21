"""
Chief of Staff AI — Backend
---------------------------
Dos funciones:
  1) POST /convert  -> recibe un PDF, lo convierte a Word (.docx) editable
                       conservando la maquetación, usando el motor pdf2docx.
  2) POST /ai       -> reenvía peticiones al modelo de Anthropic usando una
                       clave guardada de forma SEGURA en el servidor (nunca
                       en el navegador).

Arranque local:  uvicorn main:app --reload
"""

import os
import shutil
import tempfile

import requests
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pdf2docx import Converter
from starlette.background import BackgroundTask

app = FastAPI(title="Chief of Staff AI — Backend")

# --- CORS: qué webs pueden llamar a este backend ---------------------------
# En producción, pon aquí la URL exacta de tu frontend (separadas por comas).
# Ejemplo: ALLOWED_ORIGINS="https://miapp.vercel.app"
ALLOWED = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


@app.get("/health")
def health():
    """Comprobación rápida de que el servidor está vivo."""
    return {"ok": True, "ai": bool(ANTHROPIC_KEY)}


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    """Convierte un PDF subido en un .docx editable y lo devuelve para descargar."""
    name = (file.filename or "documento").lower()
    if not name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF.")

    tmp = tempfile.mkdtemp()
    pdf_path = os.path.join(tmp, "in.pdf")
    docx_path = os.path.join(tmp, "out.docx")

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path)          # <-- aquí ocurre la conversión real
        cv.close()
    except Exception as e:             # noqa: BLE001
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Error de conversión: {e}")

    out_name = (file.filename or "documento").rsplit(".", 1)[0] + ".docx"
    # BackgroundTask borra el archivo temporal DESPUÉS de enviarlo.
    return FileResponse(
        docx_path,
        filename=out_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        background=BackgroundTask(shutil.rmtree, tmp, ignore_errors=True),
    )


@app.post("/ai")
async def ai(req: Request):
    """Reenvía la petición al modelo de Anthropic con la clave del servidor."""
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=500, detail="Falta la variable ANTHROPIC_API_KEY.")
    try:
        body = await req.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Cuerpo JSON inválido.")

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=body,
        timeout=180,
    )
    try:
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=r.status_code, content={"error": r.text[:500]})
