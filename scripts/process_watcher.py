#!/usr/bin/env python3
"""
Martyr v5.2 — Watcher de Procesos
===================================
Monitorea procesos de búsqueda y pooling para evitar timeouts silenciosos.
- Timeout máximo: 30 minutos para búsquedas, 10 minutos para pooling
- Escribe heartbeat cada 30 segundos
- Mata procesos zombies
"""

import os
import sys
import time
import signal
import psutil
from datetime import datetime
from pathlib import Path

class ProcessWatcher:
    def __init__(self, timeout_seconds=1800, heartbeat_interval=30):
        self.timeout = timeout_seconds
        self.heartbeat_interval = heartbeat_interval
        self.start_time = time.time()
        self.log_file = Path("output/process_watcher.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log(self, msg, level="INFO"):
        ts = datetime.now().isoformat()
        line = f"[{ts}] [{level}] {msg}\n"
        with open(self.log_file, 'a') as f:
            f.write(line)
        print(line.strip())
        
    def heartbeat(self):
        """Escribe heartbeat y verifica timeout."""
        elapsed = time.time() - self.start_time
        self.log(f"Heartbeat: {elapsed:.0f}s / {self.timeout}s")
        
        if elapsed > self.timeout:
            self.log(f"TIMEOUT EXCEDIDO ({elapsed:.0f}s > {self.timeout}s)", "FATAL")
            self.kill_zombies()
            sys.exit(1)
            
    def kill_zombies(self):
        """Mata procesos huérfanos de Python."""
        current_pid = os.getpid()
        killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python3' and proc.info['pid'] != current_pid:
                    # No matar el propio watcher
                    if 'process_watcher' not in str(proc.info.get('cmdline', [])):
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        killed += 1
                        self.log(f"Matado proceso zombie PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return killed
        
    def watch(self, target_func, *args, **kwargs):
        """Ejecuta función con monitoreo de timeout."""
        self.log(f"Iniciando monitoreo. Timeout: {self.timeout}s")
        
        import threading
        result = [None]
        exception = [None]
        
        def wrapper():
            try:
                result[0] = target_func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
                
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()
        
        while thread.is_alive():
            self.heartbeat()
            thread.join(timeout=self.heartbeat_interval)
            
        if exception[0]:
            raise exception[0]
            
        return result[0]

if __name__ == "__main__":
    # Modo standalone: monitorear proceso actual
    watcher = ProcessWatcher()
    watcher.log("Watcher iniciado en modo standalone")
    
    # Mantener vivo escribiendo heartbeat cada 30s
    try:
        while True:
            watcher.heartbeat()
            time.sleep(watcher.heartbeat_interval)
    except KeyboardInterrupt:
        watcher.log("Watcher detenido por usuario")
