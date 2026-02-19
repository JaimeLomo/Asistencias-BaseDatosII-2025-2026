import os
import csv
import io
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

FILA_INICIO = 10

# Configuración desde secrets
token = os.environ["GITHUB_TOKEN"]
repo = os.environ["REPO"]
config = json.loads(os.environ["ASISTENCIA_CONFIG"])

fecha = config["fecha"]
hora_inicio = config["hora_inicio"]
hora_fin = config["hora_fin"]
columna = int(config["columna"])

# Cargar alumnos
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

# Obtener PR históricos
url = f"https://api.github.com/repos/{repo}/pulls?state=all&per_page=100"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json"
})
response = urllib.request.urlopen(req)
prs = json.loads(response.read().decode())

procesados = 0
for pr in prs:
    created_at = pr["created_at"]
    user = pr["user"]["login"].lower()
    dt_utc = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
    dt_spain = dt_utc.astimezone(ZoneInfo("Europe/Madrid"))

    fecha_pr = dt_spain.strftime("%Y-%m-%d")
    hora_pr = dt_spain.strftime("%H:%M")

    if fecha_pr != fecha:
        continue
    if not (hora_inicio <= hora_pr <= hora_fin):
        continue
    if user not in alumnos:
        continue

    numero = alumnos[user]

    # Enviar asistencia a Google Sheets
    data = json.dumps({
        "numero": numero,
        "columna": columna,
        "filaInicio": FILA_INICIO
    }).encode("utf-8")

    req_sheet = urllib.request.Request(os.environ["SHEETS_WEBHOOK"], data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req_sheet)
        print(f"{user}: {resp.read().decode()}")
        procesados += 1
    except Exception as e:
        print(f"Error enviando para {user}: {e}")

print(f"Total PR procesados: {procesados}")
