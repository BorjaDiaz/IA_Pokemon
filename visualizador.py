"""Analiza una ejecución del entrenamiento y guarda el resultado en runs/<fecha_hora>/analisis/.

Cada lanzamiento de train.py guarda sus datos en runs/<fecha_hora>/. Por defecto se usa la
ejecución actualizada más recientemente (--todas va a visualizaciones/todas/).

- resumen.txt: lo más importante en texto, con valoración de cada métrica (también se imprime)
- progreso.png: recompensa, mapas, baldosas y combates ganados por episodio de cada clon
- splits.png: pasos que tarda cada episodio en llegar a cada hito/mapa (si baja, va más rápido)
- mapas/<MAPA>.png: imagen real del mapa (atlas que construyen los clones) con
  un mini-cuadro de color por clon en cada casilla visitada (más intenso = más visitas)
  y el recorrido del último episodio de cada clon como línea.

Uso:
    python visualizador.py                      # última ejecución, todos sus episodios
    python visualizador.py --episodios 5        # solo los 5 últimos episodios de cada clon
    python visualizador.py --listar             # ver las ejecuciones disponibles
    python visualizador.py --run 2026-10-23     # una ejecución concreta (basta parte del nombre)
    python visualizador.py --todas              # todas las ejecuciones juntas
"""
import argparse
import glob
import json
import math
import os
import re
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw

import src.utils.config as config
from src.utils.constantes import FLAGS, MAP_NAMES
from src.env.handlers.story import cargar_records
from src.utils.map_atlas import ATLAS_DIR, TILE, merge_atlases, ensure_region, new_entry

OUTPUT_DIR = "visualizaciones"
MAPS_DIR = os.path.join(OUTPUT_DIR, "mapas")
ESCALA = 2  # cada casilla de 16 px se dibuja a 32 px
COLORES = [(230, 57, 70), (29, 120, 230), (46, 184, 92), (255, 159, 28), (155, 89, 214), (0, 200, 200),
           (255, 105, 180), (240, 228, 66), (139, 87, 42), (255, 255, 255), (120, 120, 255), (0, 120, 60)]


def color(rank):
    return COLORES[rank % len(COLORES)]


def fuentes_de_datos():
    """Ejecuciones con datos, de la más antigua a la más reciente (por última modificación).

    Incluye como "anterior" los datos de antes de existir runs/ (logs/metrics.jsonl y coordinates/).
    """
    fuentes = []
    for d in glob.glob(os.path.join(config.RUNS_DIR, "*")):
        if os.path.isdir(d):
            fuentes.append({"nombre": os.path.basename(d), "dir": d, "metrics": os.path.join(d, "metrics.jsonl"),
                            "coords": os.path.join(d, "coordinates")})
    fuentes.append({"nombre": "anterior", "dir": None, "metrics": os.path.join(config.LOG_DIR, "metrics.jsonl"),
                    "coords": os.path.join(config.BASE_DIR, "coordinates")})
    for f in fuentes:
        archivos = [f["metrics"]] + glob.glob(os.path.join(f["coords"], "*.txt"))
        f["mtime"] = max((os.path.getmtime(a) for a in archivos if os.path.exists(a)), default=None)
    return sorted((f for f in fuentes if f["mtime"]), key=lambda f: f["mtime"])


def _load_metrics(fuentes):
    """Métricas de las ejecuciones dadas. Los episodios se renumeran por clon en orden cronológico,
    para que al juntar ejecuciones no se solapen (cada lanzamiento empieza en el episodio 1)."""
    rows = []
    for orden, fuente in enumerate(fuentes):
        if os.path.exists(fuente["metrics"]):
            with open(fuente["metrics"], encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    row["_orden"] = (orden, row.get("timestamp", 0), row.get("episode", 0))
                    rows.append(row)
    contador = Counter()
    for row in sorted(rows, key=lambda r: r["_orden"]):
        contador[row.get("rank", 0)] += 1
        row["episode"] = contador[row.get("rank", 0)]
    return rows


def _load_coordinates(coords_dir):
    """{rank: [(episodio, grp, mid, x, y), ...]} en orden de visita."""
    paths = {}
    for path in glob.glob(os.path.join(coords_dir, "coords_clon_*.txt")):
        rank = int(re.search(r"coords_clon_(\d+)", path).group(1))
        puntos = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 5:
                    puntos.append(tuple(int(p) for p in parts))
        paths[rank] = puntos
    return paths


def plot_progress(metrics):
    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True, constrained_layout=True)
    fig.suptitle("Progreso por episodio", fontsize=14, fontweight="bold")
    if not metrics:
        axes[0].text(0.5, 0.5, "No hay métricas aún. Ejecuta el entrenamiento.", ha="center", va="center", transform=axes[0].transAxes)
    by_rank = defaultdict(list)
    for row in metrics:
        by_rank[row.get("rank", 0)].append(row)

    marcadores = {"no_progress": "x", "fainted": "v", "max_steps": "o"}
    for rank, rows in sorted(by_rank.items()):
        rows.sort(key=lambda r: r.get("episode", 0))
        eps = [r["episode"] for r in rows]
        col = np.array(color(rank)) / 255
        for r in rows:
            r["combates_ganados"] = combates_ganados(r)
        for ax, key in zip(axes, ("reward", "maps_discovered", "tiles_discovered", "combates_ganados")):
            ax.plot(eps, [r.get(key, 0) for r in rows], color=col, linewidth=1, alpha=0.8, label=f"Clon {rank}")
            for reason, marker in marcadores.items():
                sel = [(r["episode"], r.get(key, 0)) for r in rows if r.get("reason") == reason]
                if sel:
                    ax.scatter(*zip(*sel), color=col, marker=marker, s=18)

    for ax, title in zip(axes, ("Recompensa total", "Mapas distintos", "Baldosas distintas", "Combates ganados")):
        ax.set_ylabel(title)
        ax.grid(True, alpha=0.3)
    axes[-1].set_xlabel("Episodio  (x = sin progreso, v = debilitado, o = límite de pasos)")
    axes[-1].xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    if by_rank:
        axes[0].legend(loc="best", fontsize=8)
    path = os.path.join(OUTPUT_DIR, "progreso.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def combates_ganados(row):
    c = row.get("combates")
    return c["salvaje"]["ganado"] + c["entrenador"]["ganado"] if c else 0


def resumen_splits(metrics):
    """Splits de todos los episodios en orden cronológico (todos los clones juntos).

    Devuelve [(split, [(n_episodio_global, pasos, rank), ...], total_episodios)], con los
    hitos primero (en orden de la ruta) y después los mapas, ordenados por mediana de pasos.
    """
    episodios = sorted(metrics, key=lambda r: (r.get("timestamp", 0), r.get("episode", 0)))
    puntos = defaultdict(list)
    for i, row in enumerate(episodios, start=1):
        for split, paso in row.get("splits", {}).items():
            puntos[split].append((i, paso, row.get("rank", 0)))
    hitos = [h for h in FLAGS if h in puntos]
    # El mapa donde empieza el episodio siempre marca el paso 1: no dice nada
    mapas = [s for s in puntos if s not in FLAGS and np.median([p[1] for p in puntos[s]]) > 1]
    mapas.sort(key=lambda s: np.median([p[1] for p in puntos[s]]))
    return [(s, puntos[s], len(episodios)) for s in hitos + mapas]


def plot_splits(splits, max_paneles=12):
    splits = splits[:max_paneles]
    path = os.path.join(OUTPUT_DIR, "splits.png")
    filas = max(1, math.ceil(len(splits) / 3))
    fig, axes = plt.subplots(filas, 3, figsize=(15, 3.6 * filas), constrained_layout=True, squeeze=False)
    fig.suptitle("Pasos hasta cada hito/mapa por episodio (más bajo = más rápido)", fontsize=14, fontweight="bold")
    for ax in axes.flat[len(splits):]:
        ax.axis("off")
    if not splits:
        axes[0][0].text(0.5, 0.5, "Aún no hay splits. Ejecuta el entrenamiento.", ha="center", va="center", transform=axes[0][0].transAxes)

    for ax, (split, puntos, total) in zip(axes.flat, splits):
        xs, ys = np.array([p[0] for p in puntos]), np.array([p[1] for p in puntos])
        ax.scatter(xs, ys, c=[np.array(color(p[2])) / 255 for p in puntos], s=14, alpha=0.8)
        ventana = min(15, len(ys))
        mediana = [np.median(ys[max(0, i - ventana + 1):i + 1]) for i in range(len(ys))]
        ax.plot(xs, mediana, color="black", linewidth=1.5, label=f"mediana (últimos {ventana})")
        ax.plot(xs, np.minimum.accumulate(ys), color="crimson", linestyle="--", linewidth=1, label="récord")
        tipo = "HITO" if split in FLAGS else "mapa"
        ax.set_title(f"[{tipo}] {split}\n{len(puntos)}/{total} episodios ({100 * len(puntos) / total:.0f}%) · récord {ys.min()} pasos", fontsize=9)
        ax.set_xlabel("Episodio terminado (todos los clones, en orden)", fontsize=8)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_ylabel("Pasos", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="upper right")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def exportar_atlas():
    """Guarda en visualizaciones/atlas/<MAPA>.png el fondo de cada mapa descubierto por los clones
    (todas las ejecuciones juntas, sin recorridos). Las zonas que nadie ha visto salen en gris."""
    atlas = merge_atlases(sorted(glob.glob(os.path.join(ATLAS_DIR, "clon*.npz"))))
    for viejo in glob.glob(os.path.join(ATLAS_DIR, "*.png")):
        os.remove(viejo)
    for mapa, entry in atlas.items():
        img = entry["img"].copy()
        img[~np.kron(entry["known"], np.ones((TILE, TILE), dtype=bool))] = 45
        h, w = entry["known"].shape
        nombre = MAP_NAMES.get(mapa, f"Mapa {mapa[0]}-{mapa[1]}")
        Image.fromarray(img).resize((w * TILE * ESCALA, h * TILE * ESCALA), Image.NEAREST).save(
            os.path.join(ATLAS_DIR, f"{nombre}.png"))
    return len(atlas)


def render_map(mapa, entry, visitas, recorridos):
    """visitas: {rank: Counter((x, y))}; recorridos: {rank: [(x, y), ...]} del último episodio."""
    ox, oy = entry["origin"]
    h, w = entry["known"].shape

    # Fondo: el mapa real oscurecido para que resalten los colores; casillas nunca vistas en gris
    fondo = entry["img"].astype(np.float32) * 0.55 + 20
    mask = np.kron(entry["known"], np.ones((TILE, TILE), dtype=bool))
    fondo[~mask] = 45
    img = Image.fromarray(fondo.astype(np.uint8)).resize((w * TILE * ESCALA, h * TILE * ESCALA), Image.NEAREST).convert("RGBA")

    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(capa)
    t = TILE * ESCALA
    ranks = sorted(visitas)
    maximo = max((c for v in visitas.values() for c in v.values()), default=1)

    # Mini-cuadros dentro de cada casilla, uno por clon (posición fija por clon): 3x2 hasta 6 clones, 4x3 hasta 12
    n_slots = max(ranks, default=0) + 1
    cols = 3 if n_slots <= 6 else 4
    filas = math.ceil(n_slots / cols)
    cw, ch = t // cols, t // filas
    for rank in ranks:
        dx, dy = (rank % cols) * cw, (rank // cols) * ch
        r, g, b = color(rank)
        for (x, y), n in visitas[rank].items():
            alpha = int(255 * (0.35 + 0.65 * math.log1p(n) / math.log1p(maximo)))
            px, py = (x - ox) * t + dx, (y - oy) * t + dy
            draw.rectangle([px + 1, py + 1, px + cw - 2, py + ch - 2], fill=(r, g, b, alpha))

    # Recorrido del último episodio (se corta en saltos de más de una casilla: puertas, caídas)
    for rank, puntos in recorridos.items():
        tramos, tramo = [], []
        for punto in puntos:
            if tramo and abs(punto[0] - tramo[-1][0]) + abs(punto[1] - tramo[-1][1]) > 1:
                tramos.append(tramo)
                tramo = []
            tramo.append(punto)
        tramos.append(tramo)
        for tramo in tramos:
            if len(tramo) > 1:
                draw.line([((px - ox) * t + t // 2, (py - oy) * t + t // 2) for px, py in tramo],
                          fill=color(rank) + (255,), width=3)

    img = Image.alpha_composite(img, capa)

    # Leyenda
    nombre = MAP_NAMES.get(mapa, f"Mapa {mapa[0]}-{mapa[1]}")
    alto_leyenda = 22 + 18 * len(ranks)
    final = Image.new("RGBA", (max(img.width, 360), img.height + alto_leyenda), (25, 25, 25, 255))
    final.paste(img, (0, alto_leyenda))
    d = ImageDraw.Draw(final)
    d.text((6, 4), f"{nombre}  (grupo {mapa[0]}, mapa {mapa[1]})", fill=(255, 255, 255, 255))
    for i, rank in enumerate(ranks):
        y0 = 22 + 18 * i
        d.rectangle([6, y0 + 2, 18, y0 + 12], fill=color(rank) + (255,))
        d.text((24, y0), f"Clon {rank}: {len(visitas[rank])} casillas, {sum(visitas[rank].values())} visitas", fill=(230, 230, 230, 255))
    return final.convert("RGB"), nombre


def plot_maps(coords_por_fuente, ultimos_episodios=None):
    """coords_por_fuente: coordenadas de cada ejecución, de la más antigua a la más reciente.
    Las visitas se suman; el recorrido dibujado es el último episodio de la ejecución más reciente."""
    atlas = merge_atlases(sorted(glob.glob(os.path.join(ATLAS_DIR, "clon*.npz"))))

    visitas = defaultdict(lambda: defaultdict(Counter))  # mapa -> rank -> Counter
    recorridos = defaultdict(dict)                        # mapa -> rank -> [(x, y)]
    for n_fuente, coords in enumerate(coords_por_fuente):
        es_la_ultima = n_fuente == len(coords_por_fuente) - 1
        for rank, puntos in coords.items():
            if not puntos:
                continue
            episodios = sorted({p[0] for p in puntos})
            validos = set(episodios[-ultimos_episodios:]) if ultimos_episodios else set(episodios)
            ultimo = episodios[-1]
            for ep, grp, mid, x, y in puntos:
                if ep in validos:
                    visitas[(grp, mid)][rank][(x, y)] += 1
                if es_la_ultima and ep == ultimo:
                    recorridos[(grp, mid)].setdefault(rank, []).append((x, y))

    os.makedirs(MAPS_DIR, exist_ok=True)
    for viejo in glob.glob(os.path.join(MAPS_DIR, "*.png")):
        os.remove(viejo)

    resumen = []
    for mapa, por_clon in visitas.items():
        xs = [x for c in por_clon.values() for x, _ in c]
        ys = [y for c in por_clon.values() for _, y in c]
        # Asegurar que el lienzo cubre todas las casillas visitadas aunque el atlas no las tenga
        if mapa not in atlas:
            atlas[mapa] = new_entry(min(xs), min(ys), 1, 1)
        entry = ensure_region(atlas, mapa, min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        img, nombre = render_map(mapa, entry, por_clon, recorridos.get(mapa, {}))
        img.save(os.path.join(MAPS_DIR, f"{nombre}.png"))
        resumen.append((sum(sum(c.values()) for c in por_clon.values()), nombre, {r: len(c) for r, c in por_clon.items()}))
    return sorted(resumen, reverse=True)


def _info_run(fuentes):
    info = {}
    for f in fuentes:
        if f["dir"] and os.path.exists(os.path.join(f["dir"], "run.json")):
            with open(os.path.join(f["dir"], "run.json"), encoding="utf-8") as fh:
                info[f["nombre"]] = json.load(fh)
    return info


def _metricas_tensorboard(desde=None, hasta=None):
    """Escalares de TensorBoard (todas las ejecuciones PPO_*) entre los pasos [desde, hasta]."""
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    except ImportError:
        return {}
    series = defaultdict(list)
    for d in sorted(glob.glob(os.path.join(config.TENSORBOARD_DIR, "*"))):
        ea = EventAccumulator(d, size_guidance={"scalars": 0})
        ea.Reload()
        for tag in ea.Tags().get("scalars", []):
            for e in ea.Scalars(tag):
                if (desde is None or e.step >= desde) and (hasta is None or e.step <= hasta):
                    series[tag].append((e.step, e.value))
    return {t: sorted(v) for t, v in series.items()}


def _ini_fin(serie, n=3):
    valores = [v for _, v in serie]
    return float(np.mean(valores[:n])), float(np.mean(valores[-n:]))


def generar_resumen(fuentes, metrics, splits, mapas):
    L = []
    nombres = ", ".join(f["nombre"] for f in fuentes)
    L.append(f"RESUMEN DE LA EJECUCIÓN: {nombres}")
    L.append("=" * 78)

    infos = _info_run(fuentes)
    desde = hasta = None
    for nombre, info in infos.items():
        c = info.get("config", {})
        L.append(f"Inicio {info.get('inicio', '?')}  ·  fin {info.get('fin', 'en curso')}  ·  código {info.get('git_commit', '?')}"
                 f"  ·  modelo {info.get('modelo', '?')}")
        a, b = info.get("pasos_al_empezar"), info.get("pasos_al_terminar")
        if a is not None:
            desde = a if desde is None else min(desde, a)
        if b is not None:
            hasta = b if hasta is None else max(hasta, b)
        if a is not None and b is not None and info.get("fin"):
            from datetime import datetime
            dur = (datetime.strptime(info["fin"], "%Y-%m-%d %H:%M:%S") - datetime.strptime(info["inicio"], "%Y-%m-%d %H:%M:%S")).total_seconds()
            L.append(f"Pasos de entrenamiento {a:,} → {b:,} (+{b - a:,}) en {dur / 60:.0f} min  ·  {(b - a) / max(dur, 1):.0f} pasos/s")
        L.append(f"Config: {c.get('NUM_CLONES')} clones · lr {c.get('PPO_LEARNING_RATE')} · target_kl {c.get('PPO_TARGET_KL')}"
                 f" · gamma {c.get('PPO_GAMMA')} · ent {c.get('PPO_ENT_COEF')} · empieza en {info.get('estado_inicial')}")
    L.append("")

    # Episodios
    n = len(metrics)
    L.append(f"EPISODIOS TERMINADOS: {n}")
    if n:
        razones = Counter(r.get("reason") for r in metrics)
        nombres_razon = {"no_progress": "sin progreso", "fainted": "debilitado", "max_steps": "límite de pasos"}
        L.append("  Cómo terminan: " + " · ".join(f"{nombres_razon.get(k, k)} {100 * v / n:.0f}%" for k, v in razones.most_common()))
        ordenados = sorted(metrics, key=lambda r: r["_orden"])
        k = max(1, n // 5)
        rec_ini = np.mean([r["reward"] for r in ordenados[:k]]); rec_fin = np.mean([r["reward"] for r in ordenados[-k:]])
        len_ini = np.mean([r["steps"] for r in ordenados[:k]]); len_fin = np.mean([r["steps"] for r in ordenados[-k:]])
        L.append(f"  Recompensa media: primer 20% de episodios {rec_ini:.2f} → último 20% {rec_fin:.2f}  {_flecha(rec_fin - rec_ini, 0.1)}")
        L.append(f"  Duración media:   {len_ini:.0f} → {len_fin:.0f} pasos")
    L.append("")

    # Hitos y mapas
    L.append("HITOS Y MAPAS (en qué paso del episodio se llega; más bajo = más rápido)")
    L.append(f"  {'':38s} {'episodios':>12s} {'récord':>7s} {'mediana 1ºs 10':>15s} {'últimos 10':>11s}")
    for split, puntos, total in splits:
        pasos = [p[1] for p in puntos]
        ini, fin = np.median(pasos[:10]), np.median(pasos[-10:])
        cambio = f"{100 * (fin - ini) / ini:+.0f}%" if len(pasos) >= 20 else "(pocos datos)"
        tipo = "★" if split in FLAGS else " "
        L.append(f" {tipo}{split:38s} {len(puntos):4d} ({100 * len(puntos) / total:3.0f}%) {min(pasos):7d} {ini:15.0f} {fin:11.0f}  {cambio}")
    L.append("  ★ = hito del speedrun")
    L.append("")
    L.extend(estado_tramos(metrics))

    # Combates
    con_datos = [r for r in metrics if "combates" in r]
    L.append("COMBATES" + ("" if con_datos else ": aún no hay datos (se registran desde esta versión del código)"))
    if con_datos:
        for tipo in ("salvaje", "entrenador"):
            t = Counter()
            for r in con_datos:
                t.update(r["combates"][tipo])
            total = sum(t.values())
            if total:
                L.append(f"  {tipo:10s}: {total} combates · ganados {t['ganado']} ({100 * t['ganado'] / total:.0f}%) · "
                         f"huidos {t['huido']} · perdidos {t['perdido']}")
            else:
                L.append(f"  {tipo:10s}: ninguno")
        pasos_c = sum(r["combates"]["pasos_en_combate"] for r in con_datos)
        pasos_t = sum(r["steps"] for r in con_datos)
        L.append(f"  Tiempo en combate: {100 * pasos_c / max(pasos_t, 1):.1f}% de los pasos")
    L.append("")

    # TensorBoard
    tb = _metricas_tensorboard(desde, hasta) if (desde is not None or not infos) else {}
    # Con la ejecución aún en curso, run.json no tiene pasos_al_terminar (hasta = None)
    tramo = f", pasos {desde:,}–{f'{hasta:,}' if hasta is not None else 'ahora'}" if desde is not None else ""
    L.append(f"APRENDIZAJE (TensorBoard{tramo})")
    if not tb:
        L.append("  Sin datos de TensorBoard para este tramo.")
    else:
        def linea(tag, texto):
            if tag in tb and tb[tag]:
                L.append("  " + texto(tb[tag]))
        linea("rollout/ep_rew_mean", lambda s: f"Recompensa por episodio: {_ini_fin(s)[0]:.2f} → {_ini_fin(s)[1]:.2f}  "
              f"{_flecha(_ini_fin(s)[1] - _ini_fin(s)[0], 0.1)}")
        linea("train/explained_variance", lambda s: _valora(f"Predicción de la recompensa (explained_variance): {_ini_fin(s)[1]:.2f}",
              _ini_fin(s)[1], [(0.6, "✅ buena"), (0.3, "➖ regular"), (-9, "⚠️ mala: la red aún no entiende qué da puntos")]))
        linea("train/approx_kl", lambda s: _valora(f"Tamaño de cada actualización (approx_kl): {np.mean([v for _, v in s]):.3f}",
              -np.mean([v for _, v in s]), [(-0.02, "✅ estable"), (-0.04, "➖ algo brusca"), (-9, "⚠️ demasiado brusca")]))
        linea("train/clip_fraction", lambda s: _valora(f"clip_fraction: {np.mean([v for _, v in s]):.2f}",
              -np.mean([v for _, v in s]), [(-0.2, "✅ normal"), (-0.3, "➖ alta"), (-9, "⚠️ muy alta")]))
        linea("train/entropy_loss", lambda s: _valora(
              f"Aleatoriedad de la política: {100 * -_ini_fin(s)[1] / math.log(6):.0f}% del máximo",
              -_ini_fin(s)[1] / math.log(6), [(0.9, "➖ casi aleatoria (normal al principio)"), (0.4, "✅ aprendiendo a decidir"),
                                              (-9, "⚠️ muy decidida: vigilar que no se estanque")]))
        linea("time/fps", lambda s: f"Velocidad: {np.mean([v for _, v in s]):.0f} pasos/s")
    L.append("")

    # Récords
    records = cargar_records()
    if records:
        L.append("RÉCORDS DE TIEMPO DE PARTIDA (de todas las ejecuciones; savestates best_speedrun_*)")
        for hito, r in sorted(records.items(), key=lambda kv: kv[1]["tiempo_juego_s"]):
            minutos, segundos = divmod(r["tiempo_juego_s"], 60)
            L.append(f"  {hito:40s} {int(minutos):3d}:{segundos:05.2f}  ({r['pasos']} pasos, clon {r['clon']}, {r['run']})")
        L.append("")

    # Mapas
    L.append(f"MAPAS VISITADOS: {len(mapas)}")
    for visitas_totales, nombre, casillas in mapas:
        L.append(f"  {nombre:28s} {visitas_totales:7d} visitas · {len(casillas):2d} clones lo pisaron")
    return "\n".join(L) + "\n"


# Criterios para considerar dominado el tramo hasta un hito (ver estado_tramos)
VENTANA_TRAMO = 50       # episodios recientes que se miran
MIN_EPISODIOS_TRAMO = 20  # con menos, no hay datos suficientes
EXITO_OBJETIVO = 0.75    # lo consigue en al menos el 75% de los episodios
RAPIDEZ_OBJETIVO = 1.5   # la mediana reciente está a menos de 1,5 veces su récord
MAS_ALLA_OBJETIVO = 0.30  # en el 30% de los episodios llega a mapas nuevos después del hito


def estado_tramos(metrics):
    """¿Domina el agente el tramo desde el inicio hasta cada hito? Tres señales en los últimos episodios:
    1) lo consigue casi siempre, 2) ya va casi tan rápido como su récord, 3) sigue más allá del hito."""
    L = ["¿TRAMO DOMINADO? (últimos %d episodios)" % VENTANA_TRAMO]
    ordenados = sorted(metrics, key=lambda r: r["_orden"])
    recientes = ordenados[-VENTANA_TRAMO:]
    hitos = [h for h in FLAGS if any(h in r.get("splits", {}) for r in ordenados)]
    if not hitos:
        L.append("  Aún no se ha conseguido ningún hito.")
    if len(recientes) < MIN_EPISODIOS_TRAMO and hitos:
        L.append(f"  ⏳ Pocos datos: {len(recientes)} episodios (hacen falta {MIN_EPISODIOS_TRAMO}).")
        hitos = []
    for hito in hitos:
        con_hito = [r for r in recientes if hito in r["splits"]]
        exito = len(con_hito) / len(recientes)
        record = min(r["splits"][hito] for r in ordenados if hito in r.get("splits", {}))
        mediana = float(np.median([r["splits"][hito] for r in con_hito[-10:]])) if con_hito else None
        # "Más allá": tras el hito llega a algún mapa que no había pisado antes en ese episodio
        mas_alla = sum(1 for r in con_hito
                       if any(paso > r["splits"][hito] for nombre, paso in r["splits"].items() if nombre not in FLAGS))
        mas_alla_frac = mas_alla / len(recientes)

        ok_exito = exito >= EXITO_OBJETIVO
        ok_rapidez = mediana is not None and mediana <= RAPIDEZ_OBJETIVO * record
        ok_mas_alla = mas_alla_frac >= MAS_ALLA_OBJETIVO
        senales = [
            f"{'✅' if ok_exito else '❌'} éxito {100 * exito:.0f}% (objetivo {100 * EXITO_OBJETIVO:.0f}%)",
            f"{'✅' if ok_rapidez else '❌'} rapidez: mediana {mediana:.0f} pasos vs récord {record}"
            f" (objetivo ≤ {RAPIDEZ_OBJETIVO:g}×)" if mediana is not None else "❌ rapidez: sin datos",
            f"{'✅' if ok_mas_alla else '❌'} sigue más allá en {100 * mas_alla_frac:.0f}% (objetivo {100 * MAS_ALLA_OBJETIVO:.0f}%)",
        ]
        if ok_exito and ok_rapidez:
            veredicto = "✅ DOMINADO: ya puede practicar desde este hito (curriculum)"
        else:
            veredicto = "⏳ aún no"
        L.append(f"  Hasta {hito}: {veredicto}")
        for senal in senales:
            L.append(f"      {senal}")
    L.append("")
    return L


def _flecha(diferencia, umbral):
    return "✅ sube" if diferencia > umbral else ("⚠️ baja" if diferencia < -umbral else "➖ estable")


def _valora(texto, valor, escala):
    for minimo, etiqueta in escala:
        if valor >= minimo:
            return f"{texto}  {etiqueta}"
    return texto


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episodios", type=int, default=None, help="usar solo los N últimos episodios de cada clon")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--run", help="ejecución concreta (basta parte del nombre, p. ej. 2026-10-23_14)")
    grupo.add_argument("--todas", action="store_true", help="juntar todas las ejecuciones")
    grupo.add_argument("--listar", action="store_true", help="listar las ejecuciones disponibles y salir")
    args = parser.parse_args()

    fuentes = fuentes_de_datos()
    if args.listar or not fuentes:
        print("Ejecuciones con datos (de más antigua a más reciente):" if fuentes else "No hay datos de ninguna ejecución todavía.")
        for f in fuentes:
            n = sum(1 for _ in open(f["metrics"], encoding="utf-8")) if os.path.exists(f["metrics"]) else 0
            print(f"   {f['nombre']:22s} {n:6d} episodios terminados")
        return
    if args.run:
        fuentes = [f for f in fuentes if args.run in f["nombre"]]
        if not fuentes:
            raise SystemExit(f"No hay ninguna ejecución que contenga '{args.run}'. Usa --listar.")
    if not args.todas:
        fuentes = fuentes[-1:]
    global OUTPUT_DIR, MAPS_DIR
    if args.todas:
        OUTPUT_DIR = os.path.join("visualizaciones", "todas")
    elif fuentes[0]["dir"]:
        OUTPUT_DIR = os.path.join(fuentes[0]["dir"], "analisis")
    else:
        OUTPUT_DIR = os.path.join("visualizaciones", fuentes[0]["nombre"])
    MAPS_DIR = os.path.join(OUTPUT_DIR, "mapas")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    metrics = _load_metrics(fuentes)
    splits = resumen_splits(metrics)
    plot_progress(metrics)
    plot_splits(splits)
    mapas = plot_maps([_load_coordinates(f["coords"]) for f in fuentes], args.episodios)

    texto = generar_resumen(fuentes, metrics, splits, mapas)
    with open(os.path.join(OUTPUT_DIR, "resumen.txt"), "w", encoding="utf-8") as f:
        f.write(texto)
    print(texto)
    print(f"📁 Todo guardado en {OUTPUT_DIR}/ (resumen.txt, progreso.png, splits.png, mapas/)")
    print(f"🗺️ {exportar_atlas()} mapas limpios (lo descubierto entre todas las ejecuciones) en {ATLAS_DIR}/")


if __name__ == "__main__":
    main()
