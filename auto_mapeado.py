import json
import os

EVENTS_FILE = "eventos_descubiertos.json"
MAPS_FILE = "mapas_descubiertos.json"


import json
import os

def cargar_json(filepath):
    # Si el archivo no existe o está vacío (0 bytes), devolvemos un diccionario vacío
    if not os.path.exists(filepath) or os.stat(filepath).st_size == 0:
        return {}
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Si el archivo tiene texto basura o no es JSON válido, empezamos de cero
        print(f"⚠️ Aviso: {filepath} estaba corrupto o vacío. Creando uno nuevo.")
        return {}


def guardar_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# ==========================================
# EVENTOS
# ==========================================

def guardar_evento(addr, bit, x, y, grp, mid):
    data = cargar_json(EVENTS_FILE)

    key = f"{hex(addr)}_bit_{bit}"

    if key not in data:
        data[key] = {
            "addr": hex(addr),
            "bit": bit,
            "mapa": f"{grp},{mid}",
            "pos": {"x": x, "y": y}
        }

        guardar_json(EVENTS_FILE, data)
        print(f"🧠 Evento guardado: {key}")


# ==========================================
# MAPAS
# ==========================================

def guardar_mapa(grp, mid, x, y):
    data = cargar_json(MAPS_FILE)

    key = f"{grp},{mid}"

    if key not in data:
        data[key] = {
            "grupo": grp,
            "id": mid,
            "primer_punto": {"x": x, "y": y}
        }

        guardar_json(MAPS_FILE, data)
        print(f"🗺️ Mapa guardado: {key}")