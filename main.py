# main.py
# Punto de entrada de la aplicación FastAPI.
# Contiene: endpoints CRUD, estadísticas, manejo de errores 422,
# decorador personalizado y un endpoint asíncrono con comentarios explicativos.

import time
import logging
import functools
import pickle
import base64
from datetime import datetime
from typing import Any
from uuid import uuid4
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from models import EncuestaCompleta

# ─────────────────────────────────────────────
# Configuración del logger
# logging.basicConfig configura el formato global de los mensajes en consola.
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Instancia FastAPI
# title, description y version aparecen en Swagger UI (/docs)
# ─────────────────────────────────────────────
app = FastAPI(
    title="API de Gestión de Encuestas Poblacionales",
    description=(
        "Sistema de recolección y validación rigurosa de datos demográficos "
        "y respuestas de encuesta. Garantiza integridad estadística antes de "
        "cualquier operación analítica."
    ),
    version="1.0.0",
)

# ─────────────────────────────────────────────
# CORS — permite que navegadores externos (ej: la página de docs)
# llamen a la API desde cualquier origen.
# En producción restringir allow_origins a dominios específicos.
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Archivos estáticos / HTML propio
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

app.mount("/static", StaticFiles(directory=DOCS_DIR), name="static")

@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(DOCS_DIR / "index.html")

# ─────────────────────────────────────────────
# Almacenamiento en memoria (simula una base de datos)
# En producción esto sería reemplazado por una BD real (PostgreSQL, MongoDB, etc.)
# ─────────────────────────────────────────────
db: dict[str, dict[str, Any]] = {}


# ════════════════════════════════════════════════════════════════
# DECORADORES PERSONALIZADOS
# Un decorador en Python es una función que envuelve a otra función
# para extender su comportamiento sin modificarla directamente.
# Esto es exactamente lo que hacen @app.get, @app.post de FastAPI:
# envuelven las funciones de los endpoints para registrarlas como rutas HTTP.
# ════════════════════════════════════════════════════════════════

def log_request(func):
    """
    Decorador personalizado que registra en consola:
    - Fecha y hora de la petición
    - Nombre del endpoint ejecutado
    - Tiempo de ejecución en milisegundos

    Relación con FastAPI: @app.get/@app.post son decoradores de ruta que
    registran la función como handler de una URL. @log_request es un decorador
    de comportamiento que añade logging. Se pueden apilar (componer) ambos.
    """
    @functools.wraps(func)  # Preserva nombre y docstring de la función original
    async def wrapper(*args, **kwargs):
        inicio = time.perf_counter()
        logger.info(f"→ Ejecutando endpoint: [{func.__name__}]")
        resultado = await func(*args, **kwargs)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        logger.info(f"← [{func.__name__}] completado en {duracion_ms:.2f} ms")
        return resultado
    return wrapper


def timer(func):
    """
    Decorador que mide y loguea el tiempo de ejecución de cualquier función.
    Útil para detectar endpoints lentos en un entorno de desarrollo.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(f"⏱ Timer [{func.__name__}]: {elapsed:.2f} ms")
        return result
    return wrapper


# ════════════════════════════════════════════════════════════════
# MANEJADOR GLOBAL DE ERRORES DE VALIDACIÓN (HTTP 422)
# FastAPI lanza RequestValidationError automáticamente cuando el
# payload no cumple las reglas de los modelos Pydantic.
# Este handler intercepta ese error y devuelve una respuesta JSON
# estructurada, más amigable que la respuesta por defecto de FastAPI.
# ════════════════════════════════════════════════════════════════

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errores_detallados = []
    for error in exc.errors():
        errores_detallados.append({
            "campo": " → ".join(str(loc) for loc in error["loc"]),
            "mensaje": error["msg"],
            "tipo_error": error["type"],
            "valor_recibido": error.get("input", "N/A"),
        })

    logger.warning(
        f"⚠ Intento de ingesta inválido desde {request.client.host} | "
        f"Ruta: {request.url.path} | "
        f"Errores: {len(errores_detallados)}"
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Error de validación de datos",
            "descripcion": (
                "Uno o más campos del payload no cumplen las reglas de validación. "
                "Revise el detalle de errores a continuación."
            ),
            "total_errores": len(errores_detallados),
            "errores": errores_detallados,
            "timestamp": datetime.now().isoformat(),
        },
    )


# ════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════

# ── POST /encuestas/ ─────────────────────────────────────────────
@app.post(
    "/encuestas/",
    status_code=201,
    summary="Registrar una nueva encuesta",
    description=(
        "Recibe y valida una encuesta completa (datos del encuestado + respuestas). "
        "Si cualquier campo falla la validación, retorna HTTP 422 con detalle de errores."
    ),
    tags=["Encuestas"],
)
@log_request
async def crear_encuesta(encuesta: EncuestaCompleta):
    """
    ¿Por qué async def aquí?
    ──────────────────────────────────────────────────────────────
    En FastAPI, 'async def' permite que el servidor (ASGI) libere el hilo
    mientras espera operaciones de I/O (ej: escritura en BD, llamadas a APIs externas).
    En este caso usamos almacenamiento en memoria (sin I/O real), pero la declaración
    async def es correcta para mostrar la intención y es compatible con ASGI.

    ASGI (Asynchronous Server Gateway Interface) vs WSGI:
    - WSGI (Flask, Django clásico): síncrono, un hilo por petición.
    - ASGI (FastAPI, Starlette): asíncrono, un hilo puede manejar miles de peticiones
      concurrentes usando await para ceder el control mientras espera I/O.

    Escenario INDISPENSABLE para async/await:
    Si este endpoint tuviera que llamar a una API externa (ej: geocodificación del
    departamento) o escribir en una BD remota, 'await' permitiría atender otras
    peticiones mientras espera la respuesta, en lugar de bloquear el servidor.
    """
    encuesta_id = str(uuid4())
    db[encuesta_id] = {
        "id": encuesta_id,
        "encuesta": encuesta.model_dump(),
        "creado_en": datetime.now().isoformat(),
    }
    logger.info(f"✓ Encuesta registrada con ID: {encuesta_id}")
    return {"id": encuesta_id, **db[encuesta_id]}


# ── GET /encuestas/ ──────────────────────────────────────────────
@app.get(
    "/encuestas/",
    status_code=200,
    summary="Listar todas las encuestas",
    description="Retorna la lista completa de encuestas registradas en memoria.",
    tags=["Encuestas"],
)
@log_request
async def listar_encuestas():
    return {"total": len(db), "encuestas": list(db.values())}


# ── GET /encuestas/estadisticas/ ─────────────────────────────────
# IMPORTANTE: Este endpoint debe declararse ANTES de /encuestas/{id}
# para que FastAPI no interprete "estadisticas" como un {id} dinámico.
@app.get(
    "/encuestas/estadisticas/",
    status_code=200,
    summary="Estadísticas del repositorio de encuestas",
    description=(
        "Retorna un resumen estadístico: total de encuestas, promedio de edad, "
        "distribución por estrato socioeconómico y distribución por departamento."
    ),
    tags=["Estadísticas"],
)
@timer
async def obtener_estadisticas():
    if not db:
        return {
            "total_encuestas": 0,
            "mensaje": "No hay encuestas registradas aún.",
        }

    edades = [r["encuesta"]["encuestado"]["edad"] for r in db.values()]
    estratos = [r["encuesta"]["encuestado"]["estrato"] for r in db.values()]
    departamentos = [r["encuesta"]["encuestado"]["departamento"] for r in db.values()]

    # Distribución de estratos: conteo por cada valor
    dist_estratos: dict[int, int] = {}
    for e in estratos:
        dist_estratos[e] = dist_estratos.get(e, 0) + 1

    # Distribución de departamentos
    dist_departamentos: dict[str, int] = {}
    for d in departamentos:
        dist_departamentos[d] = dist_departamentos.get(d, 0) + 1

    return {
        "total_encuestas": len(db),
        "promedio_edad": round(sum(edades) / len(edades), 2),
        "edad_minima": min(edades),
        "edad_maxima": max(edades),
        "distribucion_estratos": dist_estratos,
        "distribucion_departamentos": dist_departamentos,
    }


# ── GET /encuestas/{id} ──────────────────────────────────────────
@app.get(
    "/encuestas/{encuesta_id}",
    status_code=200,
    summary="Obtener una encuesta por ID",
    description="Busca y retorna una encuesta específica. Retorna 404 si no existe.",
    tags=["Encuestas"],
)
@log_request
async def obtener_encuesta(encuesta_id: str):
    if encuesta_id not in db:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ninguna encuesta con ID '{encuesta_id}'."
        )
    return db[encuesta_id]


# ── PUT /encuestas/{id} ──────────────────────────────────────────
@app.put(
    "/encuestas/{encuesta_id}",
    status_code=200,
    summary="Actualizar una encuesta existente",
    description=(
        "Reemplaza completamente los datos de una encuesta existente. "
        "Los nuevos datos pasan por la misma validación que el POST."
    ),
    tags=["Encuestas"],
)
@log_request
async def actualizar_encuesta(encuesta_id: str, encuesta: EncuestaCompleta):
    if encuesta_id not in db:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ninguna encuesta con ID '{encuesta_id}'."
        )
    db[encuesta_id]["encuesta"] = encuesta.model_dump()
    db[encuesta_id]["actualizado_en"] = datetime.now().isoformat()
    logger.info(f"✓ Encuesta {encuesta_id} actualizada.")
    return {"mensaje": "Encuesta actualizada exitosamente.", "encuesta": db[encuesta_id]}


# ── DELETE /encuestas/{id} ───────────────────────────────────────
@app.delete(
    "/encuestas/{encuesta_id}",
    status_code=204,
    summary="Eliminar una encuesta",
    description="Elimina permanentemente una encuesta del repositorio. Retorna 204 sin body.",
    tags=["Encuestas"],
)
@log_request
async def eliminar_encuesta(encuesta_id: str):
    if encuesta_id not in db:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró ninguna encuesta con ID '{encuesta_id}'."
        )
    del db[encuesta_id]
    logger.info(f"✓ Encuesta {encuesta_id} eliminada.")
    return Response(status_code=204)


# ── GET /encuestas/exportar/{formato} ────────────────────────────
@app.get(
    "/encuestas/exportar/{formato}",
    status_code=200,
    summary="Exportar encuestas en JSON o Pickle",
    description=(
        "Exporta todas las encuestas en el formato solicitado.\n\n"
        "**JSON**: texto universal, legible, interoperable entre lenguajes.\n\n"
        "**Pickle**: binario exclusivo de Python, más compacto y rápido, "
        "pero NO seguro para deserializar datos externos. "
        "Se retorna codificado en Base64 para transportarlo como texto en JSON."
    ),
    tags=["Exportación"],
)
@log_request
async def exportar_encuestas(formato: str):
    if formato not in ("json", "pickle"):
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Use 'json' o 'pickle'."
        )

    datos = list(db.values())

    if formato == "json":
        datos_serializados = datos
        tamanio_bytes = len(str(datos_serializados).encode("utf-8"))
        return {
            "formato": "JSON",
            "descripcion": "Formato de texto universal. Legible por humanos y cualquier lenguaje.",
            "seguro_para_deserializar": True,
            "tamanio_aprox_bytes": tamanio_bytes,
            "total_registros": len(datos),
            "datos": datos_serializados,
        }

    else:
        pickle_bytes = pickle.dumps(datos)
        datos_b64 = base64.b64encode(pickle_bytes).decode("utf-8")
        return {
            "formato": "Pickle (Base64)",
            "descripcion": (
                "Formato binario exclusivo de Python. "
                "MÁS compacto que JSON pero NO interoperable. "
                "NUNCA deserializar datos pickle de fuentes no confiables."
            ),
            "seguro_para_deserializar": False,
            "advertencia": "Solo usar pickle para caché interno entre procesos Python confiables.",
            "tamanio_bytes_pickle": len(pickle_bytes),
            "total_registros": len(datos),
            "datos_base64": datos_b64,
            "como_deserializar": (
                "import pickle, base64; "
                "pickle.loads(base64.b64decode(datos_base64))"
            ),
        }