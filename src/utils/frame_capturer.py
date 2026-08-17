"""
Módulo para capturar frames durante el entrenamiento.
Guarda screenshots en intervalos regulares.
"""
import os
import shutil
from pathlib import Path
import numpy as np
from PIL import Image


class FrameCapturer:
    def __init__(self, output_dir: str = "capturas_steps", capture_interval: int = 100, clean_on_init: bool = False):
        """
        Capturador de frames durante entrenamiento.
        
        Args:
            output_dir: Directorio donde guardar las capturas
            capture_interval: Capturar cada N steps
            clean_on_init: Si True, borra la carpeta al inicializar (solo para rank 0)
        """
        self.output_dir = Path(output_dir)
        
        # Limpiar carpeta anterior si se solicita (solo se hace una vez, desde rank 0)
        if clean_on_init and self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            print(f"🗑️ Carpeta {output_dir} limpiada.")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.capture_interval = capture_interval
        self.step_count = 0
        self.episode_count = 0
        
    def capture_frame(self, frame: np.ndarray, info: dict = None):
        """
        Captura un frame si el step es múltiplo de capture_interval.
        
        Args:
            frame: Array de imagen (H, W, 3) o (3, H, W)
            info: Dict con info adicional (no se dibuja, solo se usa en el nombre)
        """
        self.step_count += 1
        
        # Solo capturar en intervalos
        if self.step_count % self.capture_interval != 0:
            return
        
        # Asegurar formato (H, W, 3)
        if frame.ndim == 3 and frame.shape[0] == 3:
            frame = np.transpose(frame, (1, 2, 0))
        
        # Convertir a imagen PIL
        if frame.dtype != np.uint8:
            frame = np.clip(frame * 255, 0, 255).astype(np.uint8)
        
        img = Image.fromarray(frame)
        
        # Generar nombre con info (pero sin dibujar en la imagen)
        info_str = ""
        if info:
            map_name = info.get("mapa", "?").replace(" ", "_")[:20]
            pos = info.get("pos", (0, 0))
            info_str = f"_{map_name}_pos{pos[0]}x{pos[1]}"
        
        filename = f"ep{self.episode_count:04d}_step{self.step_count:06d}{info_str}.png"
        filepath = self.output_dir / filename
        
        img.save(filepath)
        print(f"📸 Frame capturado: {filename}")
    
    def new_episode(self):
        """Incrementa el contador de episodio y resetea steps."""
        self.episode_count += 1
        self.step_count = 0
