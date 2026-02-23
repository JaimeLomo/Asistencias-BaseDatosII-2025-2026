import os
import csv
import io
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

FILA_INICIO = 10

# =============================
# Función para convertir letra de columna a número
# =============================
def col_to_num(col):
    col = str(col).upper()
    num = 0
    for c in col:
        if not 'A' <= c <= 'Z':
            raise ValueError(f"Columna inválida: {col}")
        num = num * 26 + (ord(c) - ord('A') + 1)
    return num

# =============================
# Cargar configuración y secretos
# =============================
token = os.environ["GITHUB_TOKEN"]
repo = os.environ["REPO"]
config = json.loads(os.environ["ASISTENCIA_CONFIG"])

raw_col = config["columna"]
columna = col_to_num(raw_col)

fecha = config["fecha"]
hora_inicio = config["hora_inicio"]
hora_fin = config["hora_fin"]

csv_raw = os.environ["ALUMNOS_CSV"]
f = io.StringIO(csv_raw)
reader = csv.reader(f, delimiter=';')
next(reader, None)

alumnos = {}
for row in reader:
    if len(row) < 4:
        continue
    nombre, numero, grupo, github = [x.strip() for x in row[:4]]
    alumnos[github.lower()] = numero

# =============================
# Obtener PR desde API GitHub
# =============================
url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=100"

req = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
)

response = urllib.request.urlopen(req)
prs = json.loads(response.read().decode())

procesados = 0
for pr in prs:
    user = pr["user"]["login"].lower()
    created_at = pr["created_at"]  # UTC

    if user not in alumnos:
        continue

    dt_utc = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
    dt_spain = dt_utc.astimezone(ZoneInfo("Europe/Madrid"))

    fecha_pr = dt_spain.strftime("%Y-%m-%d")
    hora_pr = dt_spain.strftime("%H:%M")

    if fecha_pr != fecha or not (hora_inicio <= hora_pr <= hora_fin):
        continue

    numero = alumnos[user]

    print("===================================")
    print("Usuario:", user)
    print("Numero real enviado:", numero)
    print("Columna:", columna)
    print("Fecha PR:", fecha_pr)
    print("Hora PR:", hora_pr)
    print("===================================")

    payload = {
        "numero": str(numero),
        "columna": columna,
        "filaInicio": FILA_INICIO
    }

    print("Payload exacto:", payload)

    data = json.dumps(payload).encode("utf-8")

    req_sheet = urllib.request.Request(
        os.environ["SHEETS_WEBHOOK"],
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req_sheet)
        respuesta = resp.read().decode()
        print(f"{user} registrado: {resp.read().decode()}")
        procesados += 1
        print("Respuesta del webhook:", respuesta)
    except Exception as e:
        print(f"Error enviando para {user}: {e}")

print(f"Proceso finalizado. Total registrados: {procesados}")
