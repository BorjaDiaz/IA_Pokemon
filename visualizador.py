import json
import os
import glob
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.utils.constantes import MAP_NAMES

OUTPUT_DIR = os.path.join("visualizaciones")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _load_metrics():
    metrics_path = os.path.join("logs", "metrics.jsonl")
    if not os.path.exists(metrics_path):
        return []

    rows = []
    with open(metrics_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def _load_coordinates():
    points = []
    zones = []
    for path in glob.glob(os.path.join("coordinates", "coords_clon_*.txt")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 4:
                        x, y, grp, mid = map(int, parts)
                        points.append((x + mid * 150, y + grp * 150))
                        zones.append((grp, mid))
        except Exception:
            pass
    return points, zones


def plot_progress_and_heatmap():
    metrics = _load_metrics()
    points, zones = _load_coordinates()

    fig, axes = plt.subplots(2, 1, figsize=(10, 10), constrained_layout=True)
    fig.suptitle("Progreso de la IA y mapa de calor", fontsize=14, fontweight="bold")

    if metrics:
        by_rank = defaultdict(list)
        for row in metrics:
            by_rank[row.get("rank", 0)].append(row)

        ax_metrics = axes[0]
        for rank, rows in sorted(by_rank.items()):
            rows = sorted(rows, key=lambda r: (r.get("episode", 0), r.get("steps", 0)))
            episodes = [r.get("episode", 0) for r in rows]
            rewards = [r.get("reward", 0.0) for r in rows]
            ax_metrics.plot(episodes, rewards, marker="o", linewidth=1.2, alpha=0.9, label=f"Clone {rank}")

        ax_metrics.set_title("Recompensa por episodio")
        ax_metrics.set_xlabel("Episodio")
        ax_metrics.set_ylabel("Recompensa")
        ax_metrics.grid(True, alpha=0.3)
        ax_metrics.legend(loc="best", fontsize=8)
    else:
        axes[0].text(0.5, 0.5, "No hay métricas aún. Ejecuta el entrenamiento para generar datos.",
                     ha="center", va="center", transform=axes[0].transAxes)
        axes[0].set_title("Recompensa por episodio")

    ax_heatmap = axes[1]
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs) - 20, max(xs) + 20
        min_y, max_y = min(ys) - 20, max(ys) + 20
        heatmap, _, _ = np.histogram2d(xs, ys, bins=80, range=[[min_x, max_x], [min_y, max_y]])
        heatmap = np.log1p(heatmap)
        img = ax_heatmap.imshow(heatmap.T, extent=[min_x, max_x, max_y, min_y], origin="upper", cmap="inferno", aspect="auto")

        zone_positions = defaultdict(list)
        for point, zone in zip(points, zones):
            zone_positions[zone].append(point)

        for (grp, mid), zone_points in sorted(zone_positions.items()):
            key = (grp, mid)
            name = MAP_NAMES.get(key, f"Zona {grp}-{mid}")
            x_center = np.mean([p[0] for p in zone_points])
            y_center = np.mean([p[1] for p in zone_points])
            ax_heatmap.text(
                x_center,
                y_center,
                name,
                color="white",
                fontsize=6,
                fontweight="bold",
                ha="center",
                va="center",
                clip_on=True,
                alpha=0.95,
                bbox=dict(boxstyle="round,pad=0.15", facecolor="black", alpha=0.45, edgecolor="none"),
            )

        ax_heatmap.set_title("Mapa de calor de posiciones visitadas")
        ax_heatmap.set_xlabel("X")
        ax_heatmap.set_ylabel("Y")
        fig.colorbar(img, ax=ax_heatmap, shrink=0.9)
    else:
        ax_heatmap.text(0.5, 0.5, "No hay coordenadas guardadas todavía.", ha="center", va="center", transform=ax_heatmap.transAxes)
        ax_heatmap.set_title("Mapa de calor de posiciones visitadas")

    output_path = os.path.join(OUTPUT_DIR, "progreso_y_mapa.png")
    fig.savefig(output_path, dpi=220)
    print(f"✅ Visualización guardada en {output_path}")


if __name__ == "__main__":
    plot_progress_and_heatmap()