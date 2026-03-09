import os
import csv
import io
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

FILA_INICIO = 10

def col_to_num(col):
    col = str(col).upper()
    num = 0
    for c in col:
        if not 'A' <= c <= 'Z':
            raise ValueError(f"Columna inválida: {col}")
        num = num * 26 + (ord(c) - ord('A') + 1)
    return num

# =============================
# Cargar configuración
# =============================
config = json.loads(os.environ["ASISTENCIA_CONFIG"])

raw_col = config["columna"]
columna = col_to_num(raw_col)

fecha = config["fecha"]
hora_inicio = config["hora_inicio"]
hora_fin = config["hora_fin"]

# =============================
# Cargar alumnos
# =============================
csv_raw = os.environ["ALUMNOS_CSV"]
f = io.StringIO(csv_raw)
reader = csv.reader(f, delimiter=';')
next(reader, None)

alumnos = {}
for row in reader:
    if len(row) < 4:
        continue
    _, numero, _, github = [x.strip() for x in row[:4]]
    alumnos[github.lower()] = numero

# =============================
# Leer evento del PR actual
# =============================
with open(os.environ["GITHUB_EVENT_PATH"]) as f:
    event = json.load(f)

pr = event["pull_request"]
user = pr["user"]["login"].lower()
created_at = pr["created_at"]

if user not in alumnos:
    print("Usuario no encontrado en CSV")
    exit()

dt_utc = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
dt_spain = dt_utc.astimezone(ZoneInfo("Europe/Madrid"))

fecha_pr = dt_spain.strftime("%Y-%m-%d")
hora_pr = dt_spain.strftime("%H:%M")

if fecha_pr != fecha or not (hora_inicio <= hora_pr <= hora_fin):
    print("PR fuera de rango horario")
    exit()

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

data = json.dumps(payload).encode("utf-8")

req_sheet = urllib.request.Request(
    os.environ["SHEETS_WEBHOOK"],
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

resp = urllib.request.urlopen(req_sheet)
respuesta = resp.read().decode()

print("Respuesta del webhook:", respuesta)