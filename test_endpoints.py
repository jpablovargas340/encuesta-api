# tests/test_endpoints.py
# Tests de integración para los endpoints de la API.
# Usa TestClient de FastAPI/Starlette que simula peticiones HTTP reales
# sin necesitar levantar el servidor con uvicorn.

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app, db

# TestClient envuelve la app FastAPI y permite hacer peticiones
# HTTP directamente en los tests sin levantar un servidor real.
client = TestClient(app)


# ══════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════

@pytest.fixture(autouse=True)
def limpiar_db():
    """
    Fixture con autouse=True: se ejecuta automáticamente antes y después
    de CADA test. Limpia la base de datos en memoria para garantizar
    que los tests son independientes entre sí.
    """
    db.clear()
    yield        # aquí corre el test
    db.clear()   # limpieza post-test


@pytest.fixture
def payload_valido():
    """Payload completo y válido para POST /encuestas/"""
    return {
        "encuestado": {
            "nombre": "Carlos Pérez",
            "edad": 35,
            "estrato": 2,
            "departamento": "Cundinamarca",
            "genero": "Masculino",
        },
        "respuestas": [
            {
                "pregunta_id": 1,
                "pregunta_texto": "¿Satisfacción con el gobierno local?",
                "respuesta": 3,
                "tipo": "likert",
            }
        ],
    }


# ══════════════════════════════════════════════
# TEST 1 — POST /encuestas/ retorna 201
# ══════════════════════════════════════════════
def test_crear_encuesta_retorna_201(payload_valido):
    """Un payload válido debe crear la encuesta y retornar HTTP 201."""
    response = client.post("/encuestas/", json=payload_valido)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data                          # debe retornar un ID
    assert data["encuesta"]["encuestado"]["nombre"] == "Carlos Pérez"


# ══════════════════════════════════════════════
# TEST 2 — POST con datos inválidos retorna 422
# ══════════════════════════════════════════════
def test_crear_encuesta_invalida_retorna_422():
    """Datos con edad fuera de rango deben retornar HTTP 422."""
    payload_invalido = {
        "encuestado": {
            "nombre": "Ana",
            "edad": 999,          # inválido
            "estrato": 3,
            "departamento": "Antioquia",
        },
        "respuestas": [
            {"pregunta_id": 1, "pregunta_texto": "Test", "respuesta": 3, "tipo": "likert"}
        ],
    }
    response = client.post("/encuestas/", json=payload_invalido)
    assert response.status_code == 422
    data = response.json()
    # Verificamos que la respuesta tiene nuestra estructura personalizada
    assert "errores" in data
    assert "total_errores" in data
    assert data["total_errores"] >= 1


# ══════════════════════════════════════════════
# TEST 3 — GET /encuestas/ retorna lista
# ══════════════════════════════════════════════
def test_listar_encuestas_vacio():
    """Con la BD vacía, debe retornar una lista vacía."""
    response = client.get("/encuestas/")
    assert response.status_code == 200
    assert response.json()["total"] == 0

def test_listar_encuestas_con_datos(payload_valido):
    """Después de crear una encuesta, el listado debe tener 1 elemento."""
    client.post("/encuestas/", json=payload_valido)
    response = client.get("/encuestas/")
    assert response.status_code == 200
    assert response.json()["total"] == 1


# ══════════════════════════════════════════════
# TEST 4 — GET /encuestas/{id} — 200 y 404
# ══════════════════════════════════════════════
def test_obtener_encuesta_existente(payload_valido):
    """Debe retornar 200 con los datos de la encuesta creada."""
    post_resp = client.post("/encuestas/", json=payload_valido)
    encuesta_id = post_resp.json()["id"]

    get_resp = client.get(f"/encuestas/{encuesta_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == encuesta_id

def test_obtener_encuesta_inexistente():
    """Un ID que no existe debe retornar 404."""
    response = client.get("/encuestas/id-que-no-existe-999")
    assert response.status_code == 404


# ══════════════════════════════════════════════
# TEST 5 — PUT /encuestas/{id} — actualización
# ══════════════════════════════════════════════
def test_actualizar_encuesta(payload_valido):
    """Actualizar una encuesta existente debe retornar 200 con datos nuevos."""
    post_resp = client.post("/encuestas/", json=payload_valido)
    encuesta_id = post_resp.json()["id"]

    payload_actualizado = dict(payload_valido)
    payload_actualizado["encuestado"] = dict(payload_valido["encuestado"])
    payload_actualizado["encuestado"]["edad"] = 40  # cambiamos la edad

    put_resp = client.put(f"/encuestas/{encuesta_id}", json=payload_actualizado)
    assert put_resp.status_code == 200
    assert put_resp.json()["encuesta"]["encuesta"]["encuestado"]["edad"] == 40

def test_actualizar_encuesta_inexistente(payload_valido):
    """Actualizar un ID inexistente debe retornar 404."""
    response = client.put("/encuestas/no-existe", json=payload_valido)
    assert response.status_code == 404


# ══════════════════════════════════════════════
# TEST 6 — DELETE /encuestas/{id} — 204 y 404
# ══════════════════════════════════════════════
def test_eliminar_encuesta(payload_valido):
    """Eliminar una encuesta existente debe retornar 204 sin body."""
    post_resp = client.post("/encuestas/", json=payload_valido)
    encuesta_id = post_resp.json()["id"]

    delete_resp = client.delete(f"/encuestas/{encuesta_id}")
    assert delete_resp.status_code == 204

    # Verificar que ya no existe
    get_resp = client.get(f"/encuestas/{encuesta_id}")
    assert get_resp.status_code == 404

def test_eliminar_encuesta_inexistente():
    """Eliminar un ID inexistente debe retornar 404."""
    response = client.delete("/encuestas/no-existe")
    assert response.status_code == 404


# ══════════════════════════════════════════════
# TEST 7 — GET /encuestas/estadisticas/
# ══════════════════════════════════════════════
def test_estadisticas_vacio():
    """Sin encuestas, estadísticas debe retornar mensaje vacío."""
    response = client.get("/encuestas/estadisticas/")
    assert response.status_code == 200
    assert response.json()["total_encuestas"] == 0

def test_estadisticas_con_datos(payload_valido):
    """Con una encuesta registrada, debe calcular estadísticas correctas."""
    client.post("/encuestas/", json=payload_valido)
    response = client.get("/encuestas/estadisticas/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_encuestas"] == 1
    assert data["promedio_edad"] == 35.0
    assert "distribucion_estratos" in data
    assert "distribucion_departamentos" in data
