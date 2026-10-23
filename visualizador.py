"""Genera las visualizaciones del entrenamiento en visualizaciones/.

Cada lanzamiento de train.py guarda sus datos en runs/<fecha_hora>/. Por defecto se usa la
ejecución actualizada más recientemente.

- progreso.png: recompensa, mapas y baldosas por episodio de cada clon
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
            fuentes.append({"nombre": os.path.basename(d), "metrics": os.path.join(d, "metrics.jsonl"),
                            "coords": os.path.join(d, "coordinates")})
    fuentes.append({"nombre": "anterior", "metrics": os.path.join(config.LOG_DIR, "metrics.jsonl"),
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
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
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
        for ax, key in zip(axes, ("reward", "maps_discovered", "tiles_discovered")):
            ax.plot(eps, [r.get(key, 0) for r in rows], color=col, linewidth=1, alpha=0.8, label=f"Clon {rank}")
            for reason, marker in marcadores.items():
                sel = [(r["episode"], r.get(key, 0)) for r in rows if r.get("reason") == reason]
                if sel:
                    ax.scatter(*zip(*sel), color=col, marker=marker, s=18)

    for ax, title in zip(axes, ("Recompensa total", "Mapas distintos", "Baldosas distintas")):
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
    print(f"📂 Ejecución{'es' if len(fuentes) > 1 else ''}: {', '.join(f['nombre'] for f in fuentes)}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    metrics = _load_metrics(fuentes)
    print(f"✅ {plot_progress(metrics)}")

    splits = resumen_splits(metrics)
    print(f"✅ {plot_splits(splits)}")
    print(f"   {'split':40s} {'logrado':>12s} {'récord':>7s} {'mediana primeros 10':>20s} {'últimos 10':>11s}")
    for split, puntos, total in splits:
        pasos = [p[1] for p in puntos]
        inicio, final = np.median(pasos[:10]), np.median(pasos[-10:])
        cambio = f"({100 * (final - inicio) / inicio:+.0f}%)" if len(pasos) >= 20 else ""
        print(f"   {split:40s} {len(puntos):5d}/{total:<6d} {min(pasos):7d} {inicio:20.0f} {final:11.0f} {cambio}")

    records = cargar_records()
    if records:
        print("🏆 Récords de tiempo de partida (savestates best_speedrun_*, todas las ejecuciones):")
        for hito, r in sorted(records.items(), key=lambda kv: kv[1]["tiempo_juego_s"]):
            minutos, segundos = divmod(r["tiempo_juego_s"], 60)
            print(f"   {hito:40s} {int(minutos):3d}:{segundos:05.2f}  (clon {r['clon']}, {r['run']})")

    resumen = plot_maps([_load_coordinates(f["coords"]) for f in fuentes], args.episodios)
    print(f"✅ {len(resumen)} mapas en {MAPS_DIR}/")
    for visitas_totales, nombre, casillas in resumen:
        por_clon = "  ".join(f"c{r}:{n}" for r, n in sorted(casillas.items()))
        print(f"   {nombre:28s} {visitas_totales:7d} visitas | casillas por clon: {por_clon}")


if __name__ == "__main__":
    main()
