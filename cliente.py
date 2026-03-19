#!/usr/bin/env python3
# cliente.py
# ─────────────────────────────────────────────────────────────────
# Script INDEPENDIENTE que actúa como cliente consumidor de la API.
# No forma parte de la API — es un programa externo que la usa.
#
# Flujo:
#   1. Lee datos desde un CSV con pandas
#   2. Envía cada fila a la API via HTTP POST usando requests
#   3. Consulta el endpoint de estadísticas
#   4. Genera un reporte estadístico con pandas y lo imprime en consola
#
# Requisitos adicionales (instalar en el mismo .venv):
#   pip install requests pandas
#
# Uso:
#   1. Levantar la API:  uvicorn main:app --reload
#   2. Ejecutar este script: python cliente.py
# ─────────────────────────────────────────────────────────────────

import requests
import pandas as pd
import json
import sys
from datetime import datetime

# URL base de la API (debe estar corriendo localmente)
BASE_URL = "http://127.0.0.1:8000"
CSV_PATH = "datos_encuesta.csv"


def cargar_csv(ruta: str) -> pd.DataFrame:
    """
    Carga el CSV de encuestas usando pandas.
    pandas.read_csv() lee el archivo y lo convierte en un DataFrame —
    una tabla en memoria con filas y columnas, similar a una hoja de Excel.
    """
    try:
        df = pd.read_csv(ruta)
        print(f"✅ CSV cargado: {len(df)} filas encontradas\n")
        return df
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo '{ruta}'")
        sys.exit(1)


def construir_payload(fila: pd.Series) -> dict:
    """
    Transforma una fila del DataFrame en el formato JSON que espera la API.
    pd.Series es una fila del DataFrame — se accede por nombre de columna.
    """
    return {
        "encuestado": {
            "nombre":       str(fila["nombre"]),
            "edad":         int(fila["edad"]),
            "estrato":      int(fila["estrato"]),
            "departamento": str(fila["departamento"]),
            "genero":       str(fila["genero"]),
        },
        "respuestas": [{
            "pregunta_id":    int(fila["pregunta_id"]),
            "pregunta_texto": str(fila["pregunta_texto"]),
            "respuesta":      int(fila["respuesta"]),
            "tipo":           str(fila["tipo"]),
        }],
    }


def enviar_encuestas(df: pd.DataFrame) -> list[dict]:
    """
    Itera el DataFrame fila por fila y envía cada encuesta a la API.
    Retorna la lista de respuestas exitosas.
    """
    print("─" * 55)
    print("📡 ENVIANDO ENCUESTAS A LA API")
    print("─" * 55)

    resultados = []
    errores = 0

    # df.iterrows() devuelve pares (índice, fila) para recorrer el DataFrame
    for i, fila in df.iterrows():
        payload = construir_payload(fila)
        try:
            response = requests.post(
                f"{BASE_URL}/encuestas/",
                json=payload,
                timeout=5,
            )
            if response.status_code == 201:
                data = response.json()
                resultados.append(data)
                print(f"  ✅ [{i+1}] {fila['nombre']:<20} → ID: {data['id'][:8]}...")
            else:
                errores += 1
                print(f"  ❌ [{i+1}] {fila['nombre']:<20} → Error {response.status_code}")
                print(f"      Detalle: {response.json().get('errores', response.text)}")
        except requests.ConnectionError:
            print("\n❌ No se pudo conectar a la API.")
            print("   Asegúrate de que uvicorn esté corriendo: uvicorn main:app --reload\n")
            sys.exit(1)

    print(f"\n  Total enviadas: {len(df)} | Exitosas: {len(resultados)} | Errores: {errores}")
    return resultados


def obtener_estadisticas_api() -> dict:
    """Consulta el endpoint de estadísticas de la API."""
    response = requests.get(f"{BASE_URL}/encuestas/estadisticas/", timeout=5)
    return response.json()


def generar_reporte(df: pd.DataFrame, stats_api: dict):
    """
    Genera un reporte estadístico combinando:
    - Análisis local con pandas (sobre el CSV)
    - Estadísticas del servidor (desde la API)
    """
    print("\n" + "═" * 55)
    print("📊 REPORTE ESTADÍSTICO — " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("═" * 55)

    # ── Estadísticas desde la API ──
    print("\n🌐 ESTADÍSTICAS DEL SERVIDOR (API):")
    print(f"   Total encuestas registradas : {stats_api['total_encuestas']}")
    print(f"   Promedio de edad            : {stats_api['promedio_edad']} años")
    print(f"   Edad mínima                 : {stats_api['edad_minima']} años")
    print(f"   Edad máxima                 : {stats_api['edad_maxima']} años")

    # ── Análisis local con pandas ──
    print("\n📈 ANÁLISIS LOCAL (pandas sobre CSV):")

    # describe() genera estadísticas descriptivas: count, mean, std, min, max, percentiles
    desc_edad = df["edad"].describe()
    print(f"\n   Distribución de edades:")
    print(f"   Media    : {desc_edad['mean']:.1f} años")
    print(f"   Desv. Est: {desc_edad['std']:.1f} años")
    print(f"   Mediana  : {df['edad'].median():.1f} años")

    # value_counts() cuenta la frecuencia de cada valor único
    print(f"\n   Distribución por estrato socioeconómico:")
    estratos = df["estrato"].value_counts().sort_index()
    for estrato, conteo in estratos.items():
        barra = "█" * conteo
        print(f"   Estrato {estrato}: {barra} ({conteo})")

    print(f"\n   Distribución por departamento:")
    deptos = df["departamento"].value_counts()
    for depto, conteo in deptos.items():
        print(f"   {depto:<25}: {conteo} encuestado(s)")

    print(f"\n   Distribución por género:")
    generos = df["genero"].value_counts()
    for genero, conteo in generos.items():
        pct = (conteo / len(df)) * 100
        print(f"   {genero:<15}: {conteo} ({pct:.1f}%)")

    # Análisis de respuestas Likert
    likert_df = df[df["tipo"] == "likert"]
    if not likert_df.empty:
        print(f"\n   Análisis de respuestas Likert:")
        print(f"   Promedio  : {likert_df['respuesta'].mean():.2f} / 5")
        print(f"   Moda      : {likert_df['respuesta'].mode()[0]} / 5")

        # groupby agrupa filas por una columna y aplica una función a cada grupo
        print(f"\n   Promedio Likert por estrato:")
        por_estrato = df.groupby("estrato")["respuesta"].mean()
        for estrato, promedio in por_estrato.items():
            print(f"   Estrato {estrato}: {promedio:.2f}")

    print("\n" + "═" * 55)
    print("✅ Reporte generado exitosamente")
    print("═" * 55)


def main():
    print("\n" + "═" * 55)
    print("🚀 CLIENTE API — ENCUESTAS POBLACIONALES")
    print("═" * 55 + "\n")

    # 1. Cargar datos del CSV
    df = cargar_csv(CSV_PATH)

    # 2. Enviar encuestas a la API
    resultados = enviar_encuestas(df)

    if not resultados:
        print("❌ No se registraron encuestas exitosas. Abortando reporte.")
        sys.exit(1)

    # 3. Obtener estadísticas del servidor
    stats = obtener_estadisticas_api()

    # 4. Generar reporte
    generar_reporte(df, stats)


if __name__ == "__main__":
    # __name__ == "__main__" garantiza que main() solo se ejecuta
    # cuando el script se corre directamente (no cuando se importa como módulo)
    main()
