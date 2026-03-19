# validators.py
# Contiene datos de referencia y funciones auxiliares usadas por los modelos Pydantic.
# Separar esto de models.py mejora la legibilidad y facilita el mantenimiento.

DEPARTAMENTOS_COLOMBIA = [
    "Amazonas", "Antioquia", "Arauca", "Atlántico", "Bolívar", "Boyacá",
    "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó", "Córdoba",
    "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira", "Magdalena",
    "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío", "Risaralda",
    "San Andrés y Providencia", "Santander", "Sucre", "Tolima",
    "Valle del Cauca", "Vaupés", "Vichada", "Bogotá D.C.",
]

# Conjunto para búsqueda O(1) — más eficiente que buscar en lista
DEPARTAMENTOS_SET = {d.lower() for d in DEPARTAMENTOS_COLOMBIA}


def es_departamento_valido(departamento: str) -> bool:
    """Verifica si el departamento pertenece a Colombia (case-insensitive)."""
    return departamento.strip().lower() in DEPARTAMENTOS_SET


def normalizar_nombre(nombre: str) -> str:
    """Elimina espacios sobrantes y convierte a Title Case."""
    return nombre.strip().title()
