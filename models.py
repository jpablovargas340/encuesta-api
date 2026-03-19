# models.py
# Define los 3 modelos Pydantic requeridos: Encuestado, RespuestaEncuesta y EncuestaCompleta.
# Pydantic v2 usa @field_validator en lugar del antiguo @validator de v1.

from typing import Optional, Union
from pydantic import BaseModel, field_validator, model_validator, Field
from validators import es_departamento_valido, normalizar_nombre


# ─────────────────────────────────────────────
# MODELO 1: Encuestado
# Representa los datos demográficos de la persona encuestada.
# ─────────────────────────────────────────────
class Encuestado(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    edad: int
    estrato: int
    departamento: str
    genero: Optional[str] = None  # Optional → el campo puede omitirse (None por defecto)

    # model_config permite agregar ejemplos que aparecen en Swagger UI
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Laura Gómez",
                    "edad": 28,
                    "estrato": 3,
                    "departamento": "Antioquia",
                    "genero": "Femenino"
                }
            ]
        }
    }

    # ── mode='before': se ejecuta ANTES de que Pydantic convierta el tipo.
    # Útil para limpiar/transformar el dato crudo que llega del JSON.
    @field_validator("nombre", mode="before")
    @classmethod
    def validar_nombre(cls, v):
        if not isinstance(v, str):
            raise ValueError("El nombre debe ser una cadena de texto.")
        return normalizar_nombre(v)  # Limpia espacios y aplica Title Case

    # ── mode='after': se ejecuta DESPUÉS de la conversión de tipo.
    # Aquí 'v' ya es un int garantizado, por eso podemos hacer comparación numérica.
    @field_validator("edad", mode="after")
    @classmethod
    def validar_edad(cls, v):
        if not (0 <= v <= 120):
            raise ValueError(f"La edad debe estar entre 0 y 120. Recibido: {v}")
        return v

    @field_validator("estrato", mode="after")
    @classmethod
    def validar_estrato(cls, v):
        if v not in range(1, 7):  # 1, 2, 3, 4, 5, 6
            raise ValueError(f"El estrato debe ser un entero entre 1 y 6. Recibido: {v}")
        return v

    @field_validator("departamento", mode="before")
    @classmethod
    def validar_departamento(cls, v):
        if not isinstance(v, str):
            raise ValueError("El departamento debe ser una cadena de texto.")
        v = v.strip()
        if not es_departamento_valido(v):
            raise ValueError(
                f"'{v}' no es un departamento válido de Colombia. "
                "Revisa la lista en /docs."
            )
        return v.title()  # Normaliza capitalización al guardar


# ─────────────────────────────────────────────
# MODELO 2: RespuestaEncuesta
# Representa la respuesta a una pregunta individual de la encuesta.
# Usa Union para aceptar distintos tipos de respuesta según la pregunta.
# ─────────────────────────────────────────────
class RespuestaEncuesta(BaseModel):
    pregunta_id: int
    pregunta_texto: str
    # Union[int, str, float] → la respuesta puede ser numérica (Likert/porcentaje)
    # o textual (respuesta abierta). Pydantic intenta convertir en el orden declarado.
    respuesta: Union[int, float, str]
    tipo: str = Field(..., pattern="^(likert|porcentaje|abierta)$")
    # pattern actúa como validador directo en el campo, solo acepta esos tres valores

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pregunta_id": 1,
                    "pregunta_texto": "¿Qué tan satisfecho está con los servicios públicos?",
                    "respuesta": 4,
                    "tipo": "likert"
                }
            ]
        }
    }

    # Validador cruzado: el rango válido depende del 'tipo' de pregunta.
    # @model_validator opera sobre el modelo completo (puede ver varios campos a la vez).
    @model_validator(mode="after")
    def validar_rango_respuesta(self):
        if self.tipo == "likert":
            if not isinstance(self.respuesta, (int, float)) or not (1 <= self.respuesta <= 5):
                raise ValueError(
                    f"Escala Likert requiere un valor entre 1 y 5. Recibido: {self.respuesta}"
                )
        elif self.tipo == "porcentaje":
            if not isinstance(self.respuesta, (int, float)) or not (0.0 <= self.respuesta <= 100.0):
                raise ValueError(
                    f"Porcentaje debe estar entre 0.0 y 100.0. Recibido: {self.respuesta}"
                )
        # tipo='abierta' no tiene restricción de rango
        return self


# ─────────────────────────────────────────────
# MODELO 3: EncuestaCompleta (modelo contenedor / raíz)
# Anida Encuestado + List[RespuestaEncuesta].
# Este es el payload que recibe el endpoint POST /encuestas/
# ─────────────────────────────────────────────
class EncuestaCompleta(BaseModel):
    encuestado: Encuestado                        # Modelo anidado
    respuestas: list[RespuestaEncuesta]           # List de modelos anidados
    version_encuesta: Optional[str] = "1.0"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "encuestado": {
                        "nombre": "Laura Gómez",
                        "edad": 28,
                        "estrato": 3,
                        "departamento": "Antioquia",
                        "genero": "Femenino"
                    },
                    "respuestas": [
                        {
                            "pregunta_id": 1,
                            "pregunta_texto": "¿Qué tan satisfecho está con los servicios públicos?",
                            "respuesta": 4,
                            "tipo": "likert"
                        },
                        {
                            "pregunta_id": 2,
                            "pregunta_texto": "¿Cuál es su nivel de ingresos respecto al salario mínimo?",
                            "respuesta": 75.5,
                            "tipo": "porcentaje"
                        }
                    ],
                    "version_encuesta": "1.0"
                }
            ]
        }
    }

    @field_validator("respuestas", mode="after")
    @classmethod
    def validar_al_menos_una_respuesta(cls, v):
        if len(v) == 0:
            raise ValueError("La encuesta debe contener al menos una respuesta.")
        return v
