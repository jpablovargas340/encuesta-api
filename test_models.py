# tests/test_models.py
# Tests unitarios para los modelos Pydantic.
# Ejecutar con: pytest tests/ -v
#
# pytest busca funciones que empiecen con "test_" y verifica que no lancen excepciones.
# ValidationError de Pydantic se usa para comprobar que datos inválidos son rechazados.

import pytest
from pydantic import ValidationError

# Agregamos el directorio raíz al path para que pytest encuentre los módulos
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Encuestado, RespuestaEncuesta, EncuestaCompleta


# ══════════════════════════════════════════════
# FIXTURES — datos reutilizables entre tests
# Un fixture es una función que provee datos de prueba.
# ══════════════════════════════════════════════

@pytest.fixture
def encuestado_valido():
    """Datos mínimos válidos para un Encuestado."""
    return {
        "nombre": "Laura Gómez",
        "edad": 28,
        "estrato": 3,
        "departamento": "Antioquia",
    }

@pytest.fixture
def respuesta_valida():
    """Respuesta Likert válida."""
    return {
        "pregunta_id": 1,
        "pregunta_texto": "¿Satisfacción con servicios públicos?",
        "respuesta": 4,
        "tipo": "likert",
    }

@pytest.fixture
def encuesta_completa_valida(encuestado_valido, respuesta_valida):
    """EncuestaCompleta válida lista para usar en tests."""
    return {
        "encuestado": encuestado_valido,
        "respuestas": [respuesta_valida],
    }


# ══════════════════════════════════════════════
# TEST 1 — Encuestado válido se crea sin errores
# ══════════════════════════════════════════════
def test_encuestado_valido(encuestado_valido):
    """Un encuestado con datos correctos debe instanciarse sin excepción."""
    enc = Encuestado(**encuestado_valido)
    assert enc.nombre == "Laura Gómez"
    assert enc.edad == 28
    assert enc.estrato == 3
    assert enc.departamento == "Antioquia"
    assert enc.genero is None  # campo opcional, debe ser None por defecto


# ══════════════════════════════════════════════
# TEST 2 — Edad fuera de rango es rechazada
# ══════════════════════════════════════════════
def test_edad_invalida_mayor_120(encuestado_valido):
    """Una edad > 120 debe lanzar ValidationError."""
    encuestado_valido["edad"] = 150
    with pytest.raises(ValidationError) as exc_info:
        Encuestado(**encuestado_valido)
    # Verificamos que el mensaje de error menciona el campo "edad"
    assert "edad" in str(exc_info.value).lower()

def test_edad_invalida_negativa(encuestado_valido):
    """Una edad negativa también debe ser rechazada."""
    encuestado_valido["edad"] = -5
    with pytest.raises(ValidationError):
        Encuestado(**encuestado_valido)


# ══════════════════════════════════════════════
# TEST 3 — Estrato fuera del rango 1-6 es rechazado
# ══════════════════════════════════════════════
def test_estrato_invalido(encuestado_valido):
    """Estratos fuera de [1,6] deben ser rechazados."""
    for estrato_invalido in [0, 7, 10, -1]:
        encuestado_valido["estrato"] = estrato_invalido
        with pytest.raises(ValidationError):
            Encuestado(**encuestado_valido)

def test_estrato_valido_todos_los_valores(encuestado_valido):
    """Los 6 estratos válidos deben aceptarse sin error."""
    for estrato in range(1, 7):
        encuestado_valido["estrato"] = estrato
        enc = Encuestado(**encuestado_valido)
        assert enc.estrato == estrato


# ══════════════════════════════════════════════
# TEST 4 — Departamento inválido es rechazado
# ══════════════════════════════════════════════
def test_departamento_invalido(encuestado_valido):
    """Un departamento que no existe en Colombia debe ser rechazado."""
    encuestado_valido["departamento"] = "Texas"
    with pytest.raises(ValidationError) as exc_info:
        Encuestado(**encuestado_valido)
    assert "departamento" in str(exc_info.value).lower()

def test_departamento_case_insensitive(encuestado_valido):
    """El departamento debe aceptarse sin importar mayúsculas/minúsculas."""
    encuestado_valido["departamento"] = "antioquia"  # minúsculas
    enc = Encuestado(**encuestado_valido)
    assert enc.departamento == "Antioquia"  # debe normalizarse a Title Case

def test_departamento_bogota(encuestado_valido):
    """Bogotá D.C. debe ser un departamento válido."""
    encuestado_valido["departamento"] = "Bogotá D.C."
    enc = Encuestado(**encuestado_valido)
    assert enc.departamento is not None


# ══════════════════════════════════════════════
# TEST 5 — Escala Likert: solo valores 1-5
# ══════════════════════════════════════════════
def test_likert_valido(respuesta_valida):
    """Valores Likert del 1 al 5 deben ser aceptados."""
    for valor in [1, 2, 3, 4, 5]:
        respuesta_valida["respuesta"] = valor
        r = RespuestaEncuesta(**respuesta_valida)
        assert r.respuesta == valor

def test_likert_invalido(respuesta_valida):
    """Valores fuera de [1,5] en tipo Likert deben ser rechazados."""
    respuesta_valida["respuesta"] = 6  # fuera de escala
    with pytest.raises(ValidationError):
        RespuestaEncuesta(**respuesta_valida)


# ══════════════════════════════════════════════
# TEST 6 — Porcentaje: rango 0.0-100.0
# ══════════════════════════════════════════════
def test_porcentaje_valido():
    """Un porcentaje dentro de [0, 100] debe ser aceptado."""
    r = RespuestaEncuesta(
        pregunta_id=2,
        pregunta_texto="¿Cobertura de salud?",
        respuesta=75.5,
        tipo="porcentaje",
    )
    assert r.respuesta == 75.5

def test_porcentaje_invalido():
    """Un porcentaje > 100 debe ser rechazado."""
    with pytest.raises(ValidationError):
        RespuestaEncuesta(
            pregunta_id=2,
            pregunta_texto="¿Cobertura?",
            respuesta=150.0,
            tipo="porcentaje",
        )


# ══════════════════════════════════════════════
# TEST 7 — EncuestaCompleta requiere al menos una respuesta
# ══════════════════════════════════════════════
def test_encuesta_sin_respuestas_rechazada(encuestado_valido):
    """Una encuesta con lista de respuestas vacía debe ser rechazada."""
    with pytest.raises(ValidationError):
        EncuestaCompleta(encuestado=encuestado_valido, respuestas=[])

def test_encuesta_completa_valida(encuesta_completa_valida):
    """Una encuesta completa y válida debe instanciarse sin error."""
    enc = EncuestaCompleta(**encuesta_completa_valida)
    assert enc.encuestado.nombre == "Laura Gómez"
    assert len(enc.respuestas) == 1
    assert enc.version_encuesta == "1.0"  # valor por defecto


# ══════════════════════════════════════════════
# TEST 8 — Nombre se normaliza a Title Case
# ══════════════════════════════════════════════
def test_nombre_normalizado(encuestado_valido):
    """El nombre debe normalizarse a Title Case y sin espacios sobrantes."""
    encuestado_valido["nombre"] = "  juan pablo   "
    enc = Encuestado(**encuestado_valido)
    assert enc.nombre == "Juan Pablo"

def test_nombre_muy_corto(encuestado_valido):
    """Un nombre de menos de 2 caracteres debe ser rechazado."""
    encuestado_valido["nombre"] = "A"
    with pytest.raises(ValidationError):
        Encuestado(**encuestado_valido)
