from modules.BlueberrySkills import BaseSkill
import os
import subprocess
import re

class VisualSkill(BaseSkill):
    """
    Smart file viewer skill that detects file types and opens them appropriately.
    Works in conjunction with AI-generated commands (Pinot) that find files.
    """
    
    def __init__(self, core):
        super().__init__("VisualSkill")
        self.core = core
        
        # Supported file types and their handlers
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
        
        # File types to exclude
        self.EXCLUDED_TYPES = ['docx', 'pptx', 'odt', 'xlsx', 'ods', 'zip', 'tar', 'gz']
        
        # Regex to extract file paths from command output
        self.FILE_PATH_REGEX =re.compile(r'(/[^\s]+\.\w+)')
        
    def show_file(self, command, response, **kwargs):
        """
        Show the last found file in appropriate viewer.
        Triggered by: "muéstramelo", "ábrelo", "quiero verlo"
        """
        # Get last found file from context
        last_file = None
        
        # Try to get from core context
        if hasattr(self.core, 'context'):
            last_file = self.core.context.get('last_found_file')
        
        # If not in context, try to extract from last command output
        if not last_file and hasattr(self.core, 'last_command_output'):
            paths = self.FILE_PATH_REGEX.findall(self.core.last_command_output)
            if paths:
                last_file = paths[0]
        
        if not last_file:
            self.speak("No tengo ningún archivo en memoria para mostrar.")
            return "No file in memory"
        
        if not os.path.exists(last_file):
            self.speak("El archivo que buscas ya no existe.")
            return "File not found"
        
        # Detect file type
        ext = last_file.split('.')[-1].lower()
        
        if ext in self.EXCLUDED_TYPES:
            self.speak(f"No puedo mostrar archivos {ext}. Usa LibreOffice o la aplicación correspondiente.")
            return "File type not supported"
        
        if ext not in self.SUPPORTED_TYPES:
            self.speak("Tipo de archivo no soportado para visualización.")
            return "Unsupported type"
        
        # Get config for this file type
        config = self.SUPPORTED_TYPES[ext]
        
        self.speak(f"Mostrando {os.path.basename(last_file)}...")
        
        if config['web']:
            # Show in web UI with PIP mode
            self._show_in_web_ui(last_file, ext)
        else:
            # Open external viewer
            self._open_external_viewer(last_file, config['apps'])
        
        return f"Opening {last_file}"
    
    def _show_in_web_ui(self, filepath, filetype):
        """Open file in web UI viewer with PIP mode"""
        try:
            # Emit to web UI to switch to PIP mode
            if hasattr(self.core, 'bus'):
                self.core.bus.emit('ui:pip_mode', {
                    'enabled': True,
                    'file_path': filepath,
                    'file_type': filetype,
                    'action': 'show'
                })
            
            # Also emit via web admin socketio if available
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
            
            self.core.app_logger.info(f"📺 Showing {filepath} in web UI (PIP mode)")
        except Exception as e:
            self.core.app_logger.error(f"Error showing file in web UI: {e}")
            self.speak("Error al mostrar el archivo en la interfaz web.")
    
    def _open_external_viewer(self, filepath, apps):
        """Open file in external application"""
        if not apps:
            self.speak("No hay visor disponible para este tipo de archivo.")
            return
        
        # Try each app until one works
        for app in apps:
            try:
                # Check if app is installed
                result = subprocess.run(['which', app], capture_output=True, text=True)
                if result.returncode == 0:
                    # App found, open file
                    subprocess.Popen([app, filepath], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    self.core.app_logger.info(f"📄 Opened {filepath} with {app}")
                    
                    # Activate PIP mode for external viewers too
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
        
        # No app worked
        self.speak(f"No pude encontrar ningún visor instalado. Necesitas instalar: {', '.join(apps)}")
    
    def close_viewer(self, command, response, **kwargs):
        """
        Close the file viewer and return to normal UI.
        Triggered by: "cierra la pantalla", "cierra el visor", "vale perfecto"
        """
        try:
            # Emit to web UI to exit PIP mode
            if hasattr(self.core, 'bus'):
                self.core.bus.emit('ui:pip_mode', {
                    'enabled': False,
                    'action': 'close'
                })
            
            # Also via web admin
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
            self.core.app_logger.info("🔚 Closing visual viewer, exiting PIP mode")
            return "Closed viewer"
        except Exception as e:
            self.core.app_logger.error(f"Error closing viewer: {e}")
            return "Error closing"
    
    def extract_file_from_output(self, command_output):
        """
        Extract file paths from command output.
        This can be called by NeoCore after executing Pinot-generated commands.
        """
        paths = self.FILE_PATH_REGEX.findall(command_output)
        if paths:
            # Store in context for later use
            if hasattr(self.core, 'context'):
                self.core.context['last_found_file'] = paths[0]
                self.core.context['all_found_files'] = paths[:5]  # Store up to 5
            return paths[0]
        return None
