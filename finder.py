import os
import json
import time
import subprocess
from modules.logger import app_logger
from modules.utils import load_json_data

class FinderSkill:
    def __init__(self, core):
        self.core = core
        self.name = "finder"
        self.cache_file = "data/finder_history.json"
        
        # Cargar configuraciones
        self.sys_logs = load_json_data("config/sys_logs.json")
        self.user_docs = load_json_data("config/user_docs.json")
        
        # Asegurar directorio de datos
        if not os.path.exists("data"):
            os.makedirs("data")
            
        # Optimizar basado en OS
        if self.core.sysadmin_manager:
            try:
                info = self.core.sysadmin_manager.get_system_info()
                distro = info.get('distro', '').lower()
                self._optimize_logs_for_distro(distro)
            except Exception as e:
                app_logger.error(f"Error optimizing logs for distro: {e}")

    def execute(self, command_text, intent_data):
        """
        Enruta la intención a manejadores específicos:
        - system_find_file: Lógica de búsqueda
        - visual_show: Lógica de vista
        - visual_close: Cerrar UI
        """
        intent_name = intent_data.get('name')
        
        if intent_name == 'system_find_file':
            return self.handle_find(command_text)
        elif intent_name == 'visual_show':
            return self.handle_show(command_text)
        elif intent_name == 'visual_close':
            return self.handle_close()
        
        return "No sé cómo manejar esa petición de búsqueda."

    def handle_find(self, text):
        """Logic to find logs or documents."""
        # 1. Chequear Palabras Clave para Logs de Sistema
        # text: "buscame el log de apache"
        for key, paths in self.sys_logs.items():
            if key in text.lower():
                # Verificar existencia
                valid_path = None
                for p in paths:
                    if os.path.exists(p):
                        valid_path = p
                        break
                
                if valid_path:
                    self._cache_result(valid_path, "log")
                    return f"He encontrado el log de {key} en {valid_path}. Di 'muestramelo' para verlo."
                else:
                    return f"No encuentro el log de {key} en las rutas esperadas."

        # 2. Chequear Atajos a Documentos de Usuario
        # text: "busca el manual de instalacion"
        if "manuals" in self.user_docs:
            for key, path in self.user_docs["manuals"].items():
                if key in text.lower() or key.replace("_", " ") in text.lower():
                     if os.path.exists(path):
                         self._cache_result(path, "pdf")
                         return f"He encontrado el manual '{key}'. Di 'abrelo' para ver."

        # 3. Búsqueda Difusa (Mango / Find)
        # Respaldo a búsqueda general si ninguna intención coincidió arriba
        # ¿Extraer nombre de archivo plausible del texto? ¿O pedir a Mango que genere el comando?
        # Pidámosle a Mango que nos genere un comando 'find', o hagamos un simple recorrido de python.
        # Requerimiento de usuario: "buscame un archivo llamado borrador.pdf"
        
        search_term = self._extract_search_term(text)
        if search_term:
             # Sanitizar
             search_term = search_term.replace(" ", "*") # Espacios difusos
             
             # Comando Locate (el más rápido)
             try:
                 cmd = ["locate", "-i", search_term]
                 result = subprocess.run(cmd, capture_output=True, text=True)
                 paths = result.stdout.strip().split('\n')
                 paths = [p for p in paths if p] # filtrar vacíos
                 
                 if paths:
                     # Filtrar por seguridad (imágenes, docs, audio)
                     safe_paths = [p for p in paths if self._is_safe_ext(p)]
                     
                     if safe_paths:
                         best = safe_paths[0] # Tomar primera coincidencia
                         ftype = "audio" if self._is_audio(best) else "doc"
                         self._cache_result(best, ftype)
                         return f"Encontré {os.path.basename(best)}. ¿Quieres verlo?"
             except Exception as e:
                 app_logger.error(f"Locate failed: {e}")
        
        return "No he encontrado nada con ese nombre."

    def handle_show(self, text):
        """Muestra el archivo cacheado."""
        cached = self._get_cached_result()
        if not cached:
            return "No tengo ningún archivo en memoria reciente."
        
        filepath = cached['path']
        ftype = cached['type']
        
        # Validar existencia
        if not os.path.exists(filepath):
            return "El archivo que encontré antes ya no existe."
            
        if ftype == 'log' or ftype == 'doc' or ftype == 'image':
            # Emitir evento SocketIO a Cliente Web vía WebAdmin (necesitamos una forma de dispararlo)
            # NeoCore debería manejar la lógica de emisión a través de la vinculación del módulo sysadmin o web_admin
            # Por ahora, devolvemos una cadena especial o llamamos a un gancho.
            # Asumiendo que existe self.core.web_admin_manager o similar.
            
            # Necesitamos construir la URL. 
            # URL = /api/viewer/serve?path=filepath (Codificada en Base64)
            import base64
            encoded_path = base64.urlsafe_b64encode(filepath.encode()).decode()
            url = f"/api/viewer/serve/{encoded_path}"
            
            # Emitir evento
            if self.core.web_server:
                self.core.web_server.socketio.emit('visual:show', {'url': url, 'type': ftype, 'filename': os.path.basename(filepath)})
                return f"Mostrando {os.path.basename(filepath)} en pantalla."
            
        elif ftype == 'audio':
            # Reproducir localmente
            self.core.speaker.play_clean(filepath) # Asumiendo que el altavoz tiene esto
            return f"Reproduciendo {os.path.basename(filepath)}."
            
        return "No puedo mostrar ese tipo de archivo."

    def handle_close(self):
        if self.core.web_server:
            self.core.web_server.socketio.emit('visual:close', {})
        return "Cerrando visor."

    def _cache_result(self, path, ftype):
        data = {
            "path": path,
            "type": ftype,
            "timestamp": time.time()
        }
        with open(self.cache_file, 'w') as f:
            json.dump(data, f)
            
    def _get_cached_result(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # Expiración 24h
                    if time.time() - data['timestamp'] < 86400:
                        return data
            except:
                pass
        return None

    def _extract_search_term(self, text):
        # Extracción muy ingenua: eliminar "busca", "encuentra", "archivo"
        removals = ["busca", "búscame", "encuentra", "el", "archivo", "fichero", "llamado", "un", "una"]
        words = text.lower().split()
        cleaned = [w for w in words if w not in removals]
        return " ".join(cleaned)

    def _is_safe_ext(self, path):
        ext = os.path.splitext(path)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.mp3', '.wav', '.ogg', '.pdf', '.md', '.txt', '.log', '.json', '.csv']
    
    def _is_audio(self, path):
         ext = os.path.splitext(path)[1].lower()
         return ext in ['.mp3', '.wav', '.ogg']

    def _optimize_logs_for_distro(self, distro):
        """
        Reordena las rutas de sys_logs en base al SO detectado.
        Prioriza:
        - Debian/Ubuntu: apache2, apt
        - Fedora/RHEL: httpd, dnf
        """
        is_debian = 'ubuntu' in distro or 'debian' in distro or 'mint' in distro or 'kali' in distro
        is_rhel = 'fedora' in distro or 'red hat' in distro or 'centos' in distro or 'rhel' in distro or 'alma' in distro
        
        app_logger.info(f"Finder Skill: Optimizing logs for distro '{distro}' (Debian={is_debian}, RHEL={is_rhel})")
        
        for key, paths in self.sys_logs.items():
            if not isinstance(paths, list): continue
            
            if is_debian:
                # Mover 'apache2' y 'apt' al principio
                paths.sort(key=lambda p: 0 if 'apache2' in p or 'apt' in p else 1)
            elif is_rhel:
                # Mover 'httpd' y 'dnf' al principio
                paths.sort(key=lambda p: 0 if 'httpd' in p or 'dnf' in p or 'yum' in p else 1)
