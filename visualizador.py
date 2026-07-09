import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from matplotlib.animation import FuncAnimation
import matplotlib.ticker as ticker

# Configuración visual estilo Cyberpunk / Radar
plt.style.use('dark_background')

# 🖼️ Ajustamos el tamaño de la figura para que tenga más altura por defecto
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_title("RADAR DE EXPLORACIÓN (Mapa de Calor de Alta Resolución)", fontsize=14, weight='bold', pad=15)
ax.invert_yaxis() 

# 🌟 ESTA ES LA CLAVE: Forzamos a que el eje X y el eje Y tengan la misma escala.
# Así los mapas volverán a ser cuadrados y no rectángulos aplastados.
ax.set_aspect('equal', adjustable='box')

# 📏 AJUSTE DE ESCALAS Y NÚMEROS LATERALES
ax.xaxis.set_major_locator(ticker.MultipleLocator(150))
ax.yaxis.set_major_locator(ticker.MultipleLocator(150))

# Números más grandes y blancos
ax.tick_params(axis='both', colors='white', labelsize=11, width=2, length=6)

# Nombres de los ejes
ax.set_xlabel("Coordenada X Global", color='#00ffff', fontsize=10, weight='bold', labelpad=10)
ax.set_ylabel("Coordenada Y Global", color='#00ffff', fontsize=10, weight='bold', labelpad=10)

# Cuadrícula de fondo
ax.grid(color='#444444', linestyle='--', linewidth=1.2, alpha=0.7)

imagenes_calor = {}
islas_descubiertas = set()
primera_vez = True

def actualizar_mapa(frame):
    global primera_vez
    archivos = glob.glob("coordinates/coords_clon_*.txt")
    if not archivos: return
        
    x_totales = []
    y_totales = []
    
    for archivo in archivos:
        try:
            with open(archivo, "r") as f:
                lineas = f.readlines()
                
            for l in lineas:
                partes = l.strip().split(",")
                if len(partes) == 4:
                    x, y, grp, mid = int(partes[0]), int(partes[1]), int(partes[2]), int(partes[3])
                    
                    x_global = x + (mid * 150)
                    y_global = y + (grp * 150)
                    
                    x_totales.append(x_global)
                    y_totales.append(y_global)
                    
                    map_key = f"{grp}-{mid}"
                    if map_key not in islas_descubiertas:
                        islas_descubiertas.add(map_key)
                        ax.text(mid * 150 + 5, grp * 150 + 15, f"Sector {map_key}", 
                                color='#00ffff', fontsize=8, alpha=0.8, weight='bold',
                                bbox=dict(facecolor='black', alpha=0.5, edgecolor='none', pad=2))
                        
        except Exception:
            pass 

    if len(x_totales) > 0:
        min_x, max_x = min(x_totales) - 20, max(x_totales) + 20
        min_y, max_y = min(y_totales) - 20, max(y_totales) + 20
        
        # Alta resolución
        resolucion_x = int((max_x - min_x) / 0.2)
        resolucion_y = int((max_y - min_y) / 0.2)
        
        if resolucion_x > 5 and resolucion_y > 5:
            heatmap, xedges, yedges = np.histogram2d(
                x_totales, y_totales, 
                bins=[resolucion_x, resolucion_y], 
                range=[[min_x, max_x], [min_y, max_y]]
            )
            
            heatmap = np.log1p(heatmap)
            
            if "global" in imagenes_calor:
                imagenes_calor["global"].remove()
                
            imagenes_calor["global"] = ax.imshow(
                heatmap.T, 
                extent=[min_x, max_x, max_y, min_y], 
                cmap='inferno', 
                origin='upper',
                alpha=0.98,
                interpolation='sinc' 
            )

    # Autoajuste de cámara SOLO la primera vez
    if primera_vez and x_totales and y_totales:
        # Hacemos que la cámara inicial tenga un tamaño cuadrado mínimo para que no se aplaste
        centro_x = (min(x_totales) + max(x_totales)) / 2
        centro_y = (min(y_totales) + max(y_totales)) / 2
        rango = 100 # Radio de visión
        
        ax.set_xlim(centro_x - rango, centro_x + rango)
        ax.set_ylim(centro_y + rango, centro_y - rango)
        primera_vez = False 


# 🖱️ CONTROLES (Zoom y movimiento)
def zoom(event):
    if event.xdata is None or event.ydata is None: return
    scale_factor = 0.8 if event.button == 'up' else 1.2
    cur_xlim, cur_ylim = ax.get_xlim(), ax.get_ylim()
    new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
    new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
    rel_x = (cur_xlim[1] - event.xdata) / (cur_xlim[1] - cur_xlim[0])
    rel_y = (cur_ylim[1] - event.ydata) / (cur_ylim[1] - cur_ylim[0])
    ax.set_xlim([event.xdata - new_width * (1 - rel_x), event.xdata + new_width * rel_x])
    ax.set_ylim([event.ydata - new_height * (1 - rel_y), event.ydata + new_height * rel_y])
    plt.draw()

def presionar_tecla(event):
    cur_xlim, cur_ylim = ax.get_xlim(), ax.get_ylim()
    ancho, alto = cur_xlim[1] - cur_xlim[0], cur_ylim[1] - cur_ylim[0]
    paso = 0.1 
    if event.key == 'right': ax.set_xlim([cur_xlim[0] + ancho * paso, cur_xlim[1] + ancho * paso])
    elif event.key == 'left': ax.set_xlim([cur_xlim[0] - ancho * paso, cur_xlim[1] - ancho * paso])
    elif event.key == 'up': ax.set_ylim([cur_ylim[0] - alto * paso, cur_ylim[1] - alto * paso])
    elif event.key == 'down': ax.set_ylim([cur_ylim[0] + alto * paso, cur_ylim[1] + alto * paso])
    plt.draw()

fig.canvas.mpl_connect('scroll_event', zoom)
fig.canvas.mpl_connect('key_press_event', presionar_tecla)

ani = FuncAnimation(fig, actualizar_mapa, interval=2000, cache_frame_data=False)

plt.show()