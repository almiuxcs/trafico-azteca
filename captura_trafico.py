# ============================================================
# Descarga de tráfico — malla Estadio Azteca
# Ventana: 10:45–17:00 CDMX | 4 segmentos | 15 min
# ============================================================
import os, requests, pandas as pd
from datetime import datetime
from pathlib import Path
import pytz

API_KEY    = os.environ["ROUTES_API_KEY"]
CDMX_TZ    = pytz.timezone("America/Mexico_City")
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
OUTPUT_CSV = Path("data/trafico_azteca.csv")

SEGMENTS = [
    {"id": "TLP_NS", "name": "Tlalpan N→S",
     "origin":      {"latitude": 19.3150, "longitude": -99.1497},
     "destination": {"latitude": 19.2880, "longitude": -99.1510}},

    {"id": "TLP_SN", "name": "Tlalpan S→N",
     "origin":      {"latitude": 19.2880, "longitude": -99.1510},
     "destination": {"latitude": 19.3150, "longitude": -99.1497}},

    {"id": "PER_EO", "name": "Periférico E→O",
     "origin":      {"latitude": 19.3020, "longitude": -99.1350},
     "destination": {"latitude": 19.3015, "longitude": -99.1620}},

    {"id": "MIR_NS", "name": "Canal Miramontes N→S",
     "origin":      {"latitude": 19.3100, "longitude": -99.1430},
     "destination": {"latitude": 19.2920, "longitude": -99.1432}},
]

def query_segment(seg: dict) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "routes.duration,"
            "routes.staticDuration,"
            "routes.distanceMeters"
        ),
    }
    body = {
        "origin":      {"location": {"latLng": seg["origin"]}},
        "destination": {"location": {"latLng": seg["destination"]}},
        "travelMode":  "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }
    try:
        r = requests.post(ROUTES_URL, json=body, headers=headers, timeout=10)
        r.raise_for_status()
        route  = r.json()["routes"][0]
        dur_s  = int(route["duration"].replace("s", ""))
        stat_s = int(route["staticDuration"].replace("s", ""))
        dist_m = route["distanceMeters"]
        return {
            "segment_id":        seg["id"],
            "segment_name":      seg["name"],
            "timestamp_utc":     datetime.utcnow().isoformat(),
            "timestamp_cdmx":    datetime.now(CDMX_TZ).isoformat(),
            "duration_s":        dur_s,
            "static_duration_s": stat_s,
            "distance_m":        dist_m,
            "congestion_ratio":  round(dur_s / stat_s, 4) if stat_s > 0 else None,
        }
    except Exception as e:
        print(f"  ✗ Error en {seg['id']}: {e}")
        return None

# --- Ejecutar una muestra ---
now_cdmx = datetime.now(CDMX_TZ)
print(f"[{now_cdmx.strftime('%H:%M')}] Ejecutando muestra...")

records = []
for seg in SEGMENTS:
    result = query_segment(seg)
    if result:
        records.append(result)
        print(f"  ✓ {seg['id']:10s}  "
              f"ratio={result['congestion_ratio']:.3f}  "
              f"dur={result['duration_s']}s")

# Append al CSV existente o crear nuevo
df_new = pd.DataFrame(records)
if OUTPUT_CSV.exists():
    df_old = pd.read_csv(OUTPUT_CSV)
    df = pd.concat([df_old, df_new], ignore_index=True)
else:
    df = df_new

df.to_csv(OUTPUT_CSV, index=False)
print(f"  → {len(df)} registros totales guardados en {OUTPUT_CSV}")
