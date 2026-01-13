from modules.skills import BaseSkill
import os
import threading
import time
from datetime import datetime

class FilesSkill(BaseSkill):
    def __init__(self, core):
        super().__init__(core)
        self.scanning = False
        self.last_scan = None
        self.last_scan = None
        
        # Force initial scan on startup (in background)
        threading.Thread(target=self.run_indexing, daemon=True).start()
        
        self.schedule_scan()

    def schedule_scan(self):
        """Inicia el scheduler de escaneo si está habilitado."""
        try:
            config = self.core.skills_config.get('files', {}).get('config', {})
            if config.get('enable_indexing', False):
                interval = config.get('scan_interval', 24) * 3600
                # Simple timer loop in a thread
                threading.Thread(target=self._scan_loop, args=(interval,), daemon=True).start()
        except Exception as e:
            self.core.app_logger.error(f"Error scheduling scan: {e}")

    def _scan_loop(self, interval):
        while True:
            self.run_indexing()
            time.sleep(interval)

    def run_indexing(self):
        """Ejecuta el escaneo e indexación."""
        if self.scanning: return
        self.scanning = True
        self.core.app_logger.info("Starting file system scan...")
        
        try:
            config = self.core.skills_config.get('files', {}).get('config', {})
            paths = config.get('scan_paths', [])
            extensions = config.get('scan_types', [])
            
            # Clear old index? Maybe partial updates are better, but for now full re-index is safer
            self.core.db.clear_file_index()
            
            count = 0
            count = 0
            for raw_path in paths:
                path = os.path.expanduser(raw_path)
                if not os.path.exists(path): continue
                for root, dirs, files in os.walk(path):
                    for file in files:
                        ext = file.split('.')[-1].lower() if '.' in file else ''
                        if not extensions or ext in extensions:
                            full_path = os.path.join(root, file)
                            try:
                                stats = os.stat(full_path)
                                self.core.db.index_file(
                                    full_path, 
                                    file, 
                                    ext, 
                                    stats.st_size, 
                                    datetime.fromtimestamp(stats.st_mtime)
                                )
                                count += 1
                            except Exception as e:
                                pass # Permission error etc
            
            self.core.app_logger.info(f"Scan complete. Indexed {count} files.")
            self.last_scan = datetime.now()
        except Exception as e:
            self.core.app_logger.error(f"Error during scan: {e}")
        finally:
            self.scanning = False

    def scan_now(self, command, response, **kwargs):
        """Comando de voz para forzar escaneo."""
        self.speak("Iniciando escaneo del sistema. Esto puede tardar un poco.")
        threading.Thread(target=self._run_scan_async).start()

    def _run_scan_async(self):
        self.run_indexing()
        self.speak("Escaneo de archivos completado.")

    def search_file(self, command, response, **kwargs):
        # "busca el archivo [nombre] en [ruta]"
        # "busca el archivo [nombre]" (default root)
        
        # Check if NLU extracted the filename (Padatious)
        target = kwargs.get('file_name')
        
        if not target:
            # Fallback to manual extraction (Legacy/Regex)
            # Clean command from triggers
            prefixes = [
                "puedes buscar un archivo que se llama",
                "busca una imagen llamada",
                "busca un archivo llamado",
                "busca el archivo", "busca archivo", "buscar archivo", 
                "puedes buscar", "encuentra el archivo", "dónde está el archivo",
                "busca", "buscar"
            ]
            
            target = command
            for prefix in prefixes:
                if target.startswith(prefix):
                    target = target[len(prefix):].strip()
                    break
        
        # Normalize phonetic extensions (Always apply this)
        replacements = {
            " punto ": ".",
            "punto ": ".",
            " jota peje": "jpg",
            " jota pe ge": "jpg",
            " pe ene ge": "png",
            " pe de efe": "pdf",
            " te equis te": "txt"
        }
        
        for spoken, written in replacements.items():
            target = target.replace(spoken, written)
            
        target = target.strip()
        path = None
        
        if " en " in target:
            parts = target.split(" en ")
            target = parts[0].strip()
            path = parts[1].strip()
            # Intentar resolver rutas comunes habladas
            if path == "mis documentos": path = os.path.expanduser("~/Documents")
            elif path == "escritorio": path = os.path.expanduser("~/Desktop")
            elif path == "descargas": path = os.path.expanduser("~/Downloads")
            elif path == "home": path = os.path.expanduser("~")

        if not target:
            self.speak("¿Qué archivo quieres buscar?")
            return

        # Try Database Search First
        config = self.core.skills_config.get('files', {}).get('config', {})
        if config.get('enable_indexing', False) and not path:
            self.speak(f"Buscando '{target}' en mi índice...")
            results = self.core.db.search_files_index(target)
            if results:
                # Save context
                self.core.context['last_found_file'] = results[0]['path']
                
                if len(results) == 1:
                    self.speak(f"Lo encontré: {results[0]['path']}")
                else:
                    self.speak(f"Encontré {len(results)} coincidencias. La primera es: {results[0]['path']}")
                return
            else:
                self.speak("No estaba en mi índice, buscando en el sistema...")

        # Fallback to live search
        # Default to user home instead of root for performance and relevance
        search_path = path if path else os.path.expanduser("~")
        self.speak(f"{response} Buscando '{target}' en {search_path}...")
        success, results = self.core.file_manager.search_files(target, search_path)
        
        if success:
            if not results:
                self.speak("No encontré ningún archivo con ese nombre.")
            elif len(results) == 1:
                self.core.context['last_found_file'] = results[0]
                self.speak(f"Lo encontré: {results[0]}")
            else:
                self.core.context['last_found_file'] = results[0]
                self.speak(f"Encontré {len(results)} coincidencias. La primera es: {results[0]}")
        else:
            self.speak(f"Hubo un error en la búsqueda: {results}")

    def read_file(self, command, response, **kwargs):
        # "lee el archivo [ruta]"
        # Difícil dictar rutas completas, mejor para archivos conocidos o relativos si tuviéramos contexto
        # Por ahora asumimos que el usuario intenta decir algo identificable o que usaremos el último encontrado (contexto)
        
        # Simplificación: "lee el archivo [nombre]" -> busca y lee el primero si es único
        target = command.replace("lee el archivo", "").replace("leer archivo", "").strip()
        
        if not target:
            self.speak("¿Qué archivo quieres leer?")
            return

        # Si parece una ruta absoluta
        if target.startswith("/"):
            path = target
        else:
            # Buscar primero
            self.speak(f"Buscando '{target}' para leerlo...")
            success, results = self.core.file_manager.search_files(target, "/")
            if not success or not results:
                self.speak("No encontré el archivo.")
                return
            path = results[0]

        self.speak(f"Leyendo {path}...")
        success, content = self.core.file_manager.read_file(path)
        
        if success:
            # Leer solo los primeros 200 caracteres o primeras 3 líneas
            lines = content.split('\n')[:3]
            preview = ". ".join(lines)
            self.speak(f"El archivo dice: {preview}...")
        else:
            self.speak(f"No pude leer el archivo: {content}")
