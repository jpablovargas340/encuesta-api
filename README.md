# API de Gestión de Encuestas Poblacionales

API REST construida con **FastAPI** y **Pydantic v2** que simula un pipeline de ingesta y validación de datos de encuestas poblacionales colombianas.

---

## Tecnologías

| Herramienta | Versión | Propósito |
|---|---|---|
| Python | 3.11+ | Lenguaje base |
| FastAPI | 0.115.0 | Framework API REST |
| Pydantic | 2.8.2 | Validación de datos |
| Uvicorn | 0.30.6 | Servidor ASGI |

---

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd encuesta-api
```

### 2. Crear el entorno virtual

Se usa **venv** (incluido en Python estándar, sin instalación extra) en lugar de conda porque el proyecto no requiere dependencias científicas con binarios nativos (numpy, pandas, etc.), y venv es más liviano y portable.

```bash
python -m venv .venv
```

### 3. Activar el entorno virtual

```bash
# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Ejecutar el servidor

```bash
uvicorn main:app --reload
```

La bandera `--reload` reinicia el servidor automáticamente al detectar cambios en el código (solo para desarrollo).

---

## Documentación interactiva

Una vez ejecutando el servidor:

| Interfaz | URL |
|---|---|
| **Swagger UI** | http://127.0.0.1:8000/docs |
| **Redoc** | http://127.0.0.1:8000/redoc |

---

## Endpoints disponibles

| Verbo | Ruta | Descripción | Status |
|---|---|---|---|
| POST | `/encuestas/` | Registrar encuesta completa | 201 |
| GET | `/encuestas/` | Listar todas las encuestas | 200 |
| GET | `/encuestas/estadisticas/` | Resumen estadístico | 200 |
| GET | `/encuestas/{id}` | Obtener encuesta por ID | 200/404 |
| PUT | `/encuestas/{id}` | Actualizar encuesta | 200/404 |
| DELETE | `/encuestas/{id}` | Eliminar encuesta | 204/404 |

---

## Ejemplo de payload (POST /encuestas/)

```json
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
```

---

## Estructura del proyecto

```
encuesta-api/
├── main.py           # Punto de entrada FastAPI + endpoints
├── models.py         # Modelos Pydantic (Encuestado, Respuesta, EncuestaCompleta)
├── validators.py     # Lista de departamentos y funciones auxiliares
├── requirements.txt  # Dependencias del proyecto
├── README.md         # Este archivo
└── .gitignore        # Archivos excluidos del control de versiones
```

---

## Flujo Git recomendado

```bash
git init
git checkout -b develop            # Rama de desarrollo
# ... trabajar en el código ...
git add .
git commit -m "feat: agregar modelos Pydantic"

git checkout main
git merge develop                  # Integrar cuando el feature esté listo
```
