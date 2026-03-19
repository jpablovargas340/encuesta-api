# 🗂️ API de Gestión de Encuestas Poblacionales

API REST construida con **FastAPI** y **Pydantic v2** que simula un pipeline de ingesta y validación de datos de encuestas poblacionales colombianas. Actúa como *aduana transaccional*: ningún dato inválido contamina el repositorio de análisis.

---

## 🌐 API en producción (despliegue en Railway)

| Interfaz | URL |
|---|---|
| **API base** | https://encuesta-api-production-9316.up.railway.app |
| **Swagger UI** | https://encuesta-api-production-9316.up.railway.app/docs |
| **Redoc** | https://encuesta-api-production-9316.up.railway.app/redoc |

> ⚠️ El plan gratuito de Railway puede suspender el servidor tras inactividad. Si la primera petición tarda, espera 30 segundos y vuelve a intentarlo.

---

## 🛠️ Tecnologías

| Herramienta | Versión | Propósito |
|---|---|---|
| Python | 3.11+ | Lenguaje base |
| FastAPI | 0.115.12 | Framework API REST (ASGI) |
| Pydantic | 2.10.6 | Validación de datos y modelos |
| Uvicorn | 0.34.0 | Servidor ASGI de alto rendimiento |
| pytest | 8.3.2 | Tests unitarios y de integración |
| httpx | 0.27.2 | Cliente HTTP para TestClient |
| requests | 2.32.3 | Cliente HTTP para script consumidor |
| pandas | 2.2.3 | Análisis estadístico en cliente CSV |

---

## 📁 Estructura del proyecto

```
encuesta-api/
├── main.py               # Punto de entrada FastAPI + todos los endpoints
├── models.py             # Modelos Pydantic (Encuestado, RespuestaEncuesta, EncuestaCompleta)
├── validators.py         # Lista de 33 departamentos colombianos y funciones auxiliares
├── cliente.py            # Script consumidor: carga CSV y genera reporte con pandas
├── datos_encuesta.csv    # Dataset de ejemplo con 10 encuestas
├── requirements.txt      # Dependencias del proyecto
├── render.yaml           # Configuración de despliegue
├── .python-version       # Versión de Python forzada (3.11.9)
├── README.md             # Este archivo
├── .gitignore            # Archivos excluidos del control de versiones
├── docs/
│   └── index.html        # Página web de documentación interactiva
└── tests/
    ├── __init__.py
    ├── test_models.py     # 8 tests de modelos Pydantic
    └── test_endpoints.py  # 7 tests de endpoints HTTP
```

---

## ⚙️ Instalación y ejecución local

### 1. Clonar el repositorio

```bash
git clone https://github.com/jpablovargas340/encuesta-api.git
cd encuesta-api
```

### 2. Crear el entorno virtual

Se usa **venv** (incluido en Python estándar) en lugar de conda porque el proyecto no requiere dependencias con binarios nativos complejos, y venv es más liviano, portable y no requiere instalación adicional.

```bash
python -m venv .venv
```

### 3. Activar el entorno virtual

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Sabrás que está activo cuando veas `(.venv)` al inicio de la línea en la terminal.

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Ejecutar el servidor

```bash
uvicorn main:app --reload
```

La bandera `--reload` reinicia el servidor automáticamente al detectar cambios en el código. Solo usar en desarrollo, nunca en producción.

### 6. Verificar que funciona

Abre en el navegador: **http://127.0.0.1:8000/docs**

Deberías ver el Swagger UI con todos los endpoints listos para probar.

---

## 📡 Endpoints disponibles

| Verbo | Ruta | Descripción | Status Code |
|---|---|---|---|
| `POST` | `/encuestas/` | Registrar encuesta completa | 201 Created |
| `GET` | `/encuestas/` | Listar todas las encuestas | 200 OK |
| `GET` | `/encuestas/estadisticas/` | Resumen estadístico | 200 OK |
| `GET` | `/encuestas/{id}` | Obtener encuesta por ID | 200 OK / 404 |
| `PUT` | `/encuestas/{id}` | Actualizar encuesta existente | 200 OK / 404 |
| `DELETE` | `/encuestas/{id}` | Eliminar encuesta | 204 No Content / 404 |
| `GET` | `/encuestas/exportar/json` | Exportar datos en JSON | 200 OK |
| `GET` | `/encuestas/exportar/pickle` | Exportar en Pickle (Base64) | 200 OK |

---

## 📦 Modelos Pydantic

### `Encuestado`
| Campo | Tipo | Restricción |
|---|---|---|
| nombre | `str` | 2–100 chars, normalizado a Title Case |
| edad | `int` | 0 ≤ edad ≤ 120 |
| estrato | `int` | 1, 2, 3, 4, 5 o 6 |
| departamento | `str` | Lista oficial de 33 departamentos de Colombia |
| genero | `Optional[str]` | Campo opcional |

### `RespuestaEncuesta`
| Campo | Tipo | Restricción |
|---|---|---|
| pregunta_id | `int` | Requerido |
| pregunta_texto | `str` | Requerido |
| respuesta | `Union[int, float, str]` | Rango según tipo |
| tipo | `str` | Solo: `likert`, `porcentaje`, `abierta` |

### `EncuestaCompleta`
Modelo contenedor que anida `Encuestado` + `List[RespuestaEncuesta]`. Requiere mínimo una respuesta.

---

## 🛡️ Validaciones implementadas

| Campo | Modo | Regla |
|---|---|---|
| `nombre` | `before` | Limpia espacios y normaliza a Title Case |
| `edad` | `after` | Rango biológico: 0–120 |
| `estrato` | `after` | Sistema colombiano: 1–6 |
| `departamento` | `before` | Valida contra lista oficial de Colombia |
| `respuesta Likert` | model | Escala 1–5 |
| `respuesta porcentaje` | model | Rango 0.0–100.0 |

Cualquier dato inválido retorna **HTTP 422** con JSON estructurado que detalla exactamente qué campo falló y por qué.

---

## 🧪 Ejecutar tests

```bash
pytest tests/ -v
```

Resultado esperado:
```
tests/test_models.py::test_encuestado_valido              PASSED
tests/test_models.py::test_edad_invalida_mayor_120        PASSED
tests/test_endpoints.py::test_crear_encuesta_retorna_201  PASSED
...
15 passed in 1.2s
```

---

## 📊 Script cliente (bonus)

```bash
pip install requests pandas
python cliente.py
```

Carga 10 encuestas desde `datos_encuesta.csv`, las envía a la API y genera un reporte estadístico en consola.

---

## 🔑 Conceptos clave

**¿Por qué `async def`?**
FastAPI corre sobre ASGI (Uvicorn). Con `async def`, el servidor puede atender otras peticiones mientras espera I/O, en lugar de bloquear el hilo como haría WSGI (Flask/Django clásico).

**¿Por qué `mode='before'` vs `mode='after'`?**
- `before`: recibe el dato crudo antes de la conversión de tipo. Útil para limpiar strings.
- `after`: recibe el dato ya convertido. Útil para validar rangos numéricos.

**¿Por qué JSON y no Pickle para APIs?**
JSON es texto universal, legible por cualquier lenguaje. Pickle es binario exclusivo de Python — más rápido pero inseguro para deserializar datos de fuentes externas.

---

## 🔀 Estrategia Git

```bash
git checkout -b develop     # rama de desarrollo
git add .
git commit -m "feat: descripción del cambio"
git push

git checkout main
git merge develop           # integrar cuando el feature esté listo
git push
```
