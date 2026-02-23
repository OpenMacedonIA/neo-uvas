from modules.BlueberrySkills import BaseSkill
import os
import subprocess
import re

class VisualSkill(BaseSkill):
    """
    Skill de visor inteligente de archivos que detecta tipos de archivo y los abre adecuadamente.
    Funciona junto con comandos generados por IA (Pinot) que buscan archivos.
    """
    
    def __init__(self, core):
        super().__init__("VisualSkill")
        self.core = core
        
        # Tipos de archivo soportados y sus manejadores
        self.SUPPORTED_TYPES = {
            'pdf': {'apps': ['evince', 'okular', 'xpdf'], 'web': False},
            'jpg': {'apps': ['feh', 'eog'], 'web': True},
            'jpeg': {'apps': ['feh', 'eog'], 'web': True},
            'png': {'apps': ['feh', 'eog'], 'web': True},
            'gif': {'apps': ['feh', 'eog'], 'web': True},
            'webp': {'apps': ['feh', 'eog'], 'web': True},
            'txt': {'apps': None, 'web': True},
            'md': {'apps': None, 'web': True},
            'log': {'apps': None, 'web': True},
            'conf': {'apps': None, 'web': True},
            'py': {'apps': None, 'web': True},
            'js': {'apps': None, 'web': True},
            'sh': {'apps': None, 'web': True},
            'json': {'apps': None, 'web': True},
            'yaml': {'apps': None, 'web': True},
            'yml': {'apps': None, 'web': True},
            'xml': {'apps': None, 'web': True},
            'html': {'apps': None, 'web': True},
            'css': {'apps': None, 'web': True},
        }
        
        # Tipos de archivo a excluir
        self.EXCLUDED_TYPES = ['docx', 'pptx', 'odt', 'xlsx', 'ods', 'zip', 'tar', 'gz']
        
        # Expresión regular para extraer rutas de archivo de la salida del comando
        self.FILE_PATH_REGEX =re.compile(r'(/[^\s]+\.\w+)')
        
    def show_file(self, command, response, **kwargs):
        """
        Muestra el último archivo encontrado en el visor adecuado.
        Activado por: "muéstramelo", "ábrelo", "quiero verlo"
        """
        # Obtener el último archivo encontrado del contexto
        last_file = None
        
        # Intentar obtener del contexto del core
        if hasattr(self.core, 'context'):
            last_file = self.core.context.get('last_found_file')
        
        # Si no está en contexto, intentar extraer de la salida del último comando
        if not last_file and hasattr(self.core, 'last_command_output'):
            paths = self.FILE_PATH_REGEX.findall(self.core.last_command_output)
            if paths:
                last_file = paths[0]
        
        if not last_file:
            self.speak("No tengo ningún archivo en memoria para mostrar.")
            return "No hay archivo en memoria"
        
        if not os.path.exists(last_file):
            self.speak("El archivo que buscas ya no existe.")
            return "Archivo no encontrado"
        
        # Detectar tipo de archivo
        ext = last_file.split('.')[-1].lower()
        
        if ext in self.EXCLUDED_TYPES:
            self.speak(f"No puedo mostrar archivos {ext}. Usa LibreOffice o la aplicación correspondiente.")
            return "Tipo de archivo no soportado"
        
        if ext not in self.SUPPORTED_TYPES:
            self.speak("Tipo de archivo no soportado para visualización.")
            return "Tipo no soportado"
        
        # Obtener configuración para este tipo de archivo
        config = self.SUPPORTED_TYPES[ext]
        
        self.speak(f"Mostrando {os.path.basename(last_file)}...")
        
        if config['web']:
            # Mostrar en la interfaz web con modo PIP
            self._show_in_web_ui(last_file, ext)
        else:
            # Abrir visor externo
            self._open_external_viewer(last_file, config['apps'])
        
        return f"Abriendo {last_file}"
    
    def _show_in_web_ui(self, filepath, filetype):
        """Abre archivo en el visor de la interfaz web con modo PIP"""
        try:
            # Emitir a la interfaz web para cambiar a modo PIP
            if hasattr(self.core, 'bus'):
                self.core.bus.emit('ui:pip_mode', {
                    'enabled': True,
                    'file_path': filepath,
                    'file_type': filetype,
                    'action': 'show'
                })
            
            # También emitir a través de web admin socketio si está disponible
            try:
                import modules.web_admin as web_admin
                if hasattr(web_admin, 'socketio'):
                    web_admin.socketio.emit('ui:pip_mode', {
                        'enabled': True,
                        'file_path': filepath,
                        'file_type': filetype,
                        'action': 'show'
                    }, namespace='/')
            except:
                pass
            
            self.core.app_logger.info(f" Showing {filepath} in web UI (PIP mode)")
        except Exception as e:
            self.core.app_logger.error(f"Error showing file in web UI: {e}")
            self.speak("Error al mostrar el archivo en la interfaz web.")
    
    def _open_external_viewer(self, filepath, apps):
        """Abre archivo en aplicación externa"""
        if not apps:
            self.speak("No hay visor disponible para este tipo de archivo.")
            return
        
        # Probar cada aplicación hasta que una funcione
        for app in apps:
            try:
                # Comprobar si la aplicación está instalada
                result = subprocess.run(['which', app], capture_output=True, text=True)
                if result.returncode == 0:
                    # Aplicación encontrada, abrir archivo
                    subprocess.Popen([app, filepath], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    self.core.app_logger.info(f" Opened {filepath} with {app}")
                    
                    # Activar modo PIP también para visores externos
                    try:
                        import modules.web_admin as web_admin
                        if hasattr(web_admin, 'socketio'):
                            web_admin.socketio.emit('ui:pip_mode', {
                                'enabled': True,
                                'file_path': filepath,
                                'file_type': 'external',
                                'viewer_app': app,
                                'action': 'show'
                            }, namespace='/')
                    except:
                        pass
                    
                    return
            except Exception as e:
                self.core.app_logger.debug(f"Failed to open with {app}: {e}")
                continue
        
        # Ninguna aplicación funcionó
        self.speak(f"No pude encontrar ningún visor instalado. Necesitas instalar: {', '.join(apps)}")
    
    def close_viewer(self, command, response, **kwargs):
        """
        Cierra el visor de archivos y vuelve a la interfaz normal.
        Activado por: "cierra la pantalla", "cierra el visor", "vale perfecto"
        """
        try:
            # Emitir a la interfaz web para salir del modo PIP
            if hasattr(self.core, 'bus'):
                self.core.bus.emit('ui:pip_mode', {
                    'enabled': False,
                    'action': 'close'
                })
            
            # También vía web admin
            try:
                import modules.web_admin as web_admin
                if hasattr(web_admin, 'socketio'):
                    web_admin.socketio.emit('ui:pip_mode', {
                        'enabled': False,
                        'action': 'close'
                    }, namespace='/')
            except:
                pass
            
            self.speak("Cerrando visualización.")
            self.core.app_logger.info(" Closing visual viewer, exiting PIP mode")
            return "Visor cerrado"
        except Exception as e:
            self.core.app_logger.error(f"Error closing viewer: {e}")
            return "Error al cerrar"
    
    def extract_file_from_output(self, command_output):
        """
        Extrae rutas de archivos de la salida de los comandos.
        Esto puede ser llamado por NeoCore después de ejecutar comandos generados por Pinot.
        """
        paths = self.FILE_PATH_REGEX.findall(command_output)
        if paths:
            # Almacenar en contexto para uso posterior
            if hasattr(self.core, 'context'):
                self.core.context['last_found_file'] = paths[0]
                self.core.context['all_found_files'] = paths[:5]  # Almacenar hasta 5
            return paths[0]
        return None
