"""
Skill de Seguridad - Control de escaneo antivirus y cuarentena.
Permite al usuario escanear archivos/directorios por voz.
"""

from modules.BlueberrySkills.base_skill import BaseSkill
import os
import logging

logger = logging.getLogger("SecuritySkill")


class SecuritySkill(BaseSkill):
    """
    Skill para seguridad y escaneo antivirus.
    Usa el VirusScanner integrado en WatermelonGuard.
    """
    
    def __init__(self, core):
        super().__init__(core)
        # Acceder al scanner a través de guard
        self.virus_scanner = None
        if hasattr(core, 'guard') and core.guard:
            self.virus_scanner = core.guard.virus_scanner
        
        # Registrar intents (para fallback cuando router no categoriza bien)
        self.register_intent("scan_downloads", 
                           ["escanea mis descargas", "busca virus en descargas", "analiza las descargas"],
                           "scan_downloads")
        self.register_intent("scan_file",
                           ["escanea el archivo", "busca virus en este archivo", "analiza el fichero"],
                           "scan_file")
        self.register_intent("list_quarantine",
                           ["lista la cuarentena", "qué hay en cuarentena", "ver cuarentena"],
                           "list_quarantine")
        self.register_intent("update_signatures",
                           ["actualiza las firmas de virus", "actualiza antivirus", "update virus"],
                           "update_virus_signatures")
        self.register_intent("security_status",
                           ["estado de seguridad", "cómo está la seguridad", "reporte de seguridad"],
                           "security_status")
    
    def register_intent(self, name, triggers, action):
        """Registra un intent para este skill."""
        if hasattr(self.core, 'skills_service') and self.core.skills_service:
            intent = {
                'name': name,
                'triggers': triggers,
                'action': action,
                'skill': self
            }
            self.core.skills_service.register_skill_intent(intent)
    
    def scan_downloads(self, command, response, **kwargs):
        """
        Escanea carpeta de descargas completa.
        Comando: "escanea mis descargas", "busca virus en descargas"
        """
        if not self.virus_scanner or not self.virus_scanner.clamav_available:
            self.speak("El sistema de escaneo de virus no está disponible. Instala ClamAV con: sudo apt install clamav")
            return
        
        self.speak("Escaneando Descargas, esto puede tardar un momento...")
        
        downloads = os.path.expanduser("~/Downloads")
        if not os.path.exists(downloads):
            self.speak("No encontré la carpeta de Descargas")
            return
        
        infected, total = self.virus_scanner.scan_directory(downloads, recursive=False)
        
        if infected:
            count = len(infected)
            files = ", ".join([os.path.basename(f) for f in infected[:3]])  # Max 3 nombres
            if count > 3:
                files += f" y {count - 3} más"
            self.speak(f"ALERTA: {count} archivos infectados encontrados: {files}. Movidos a cuarentena.")
        else:
            self.speak(f"Escaneo completo. {total} archivos analizados, ninguno infectado.")
    
    def scan_file(self, command, response, **kwargs):
        """
        Escanea archivo específico.
        Comando: "escanea el archivo documento.pdf"
        """
        if not self.virus_scanner or not self.virus_scanner.clamav_available:
            self.speak("El sistema de escaneo de virus no está disponible.")
            return
        
        # Intentar extraer nombre de archivo del comando
        # Simplificado: buscar palabras después de "archivo" o "fichero"
        words = command.lower().split()
        filename = None
        
        try:
            if "archivo" in words:
                idx = words.index("archivo") + 1
                filename = " ".join(words[idx:])
            elif "fichero" in words:
                idx = words.index("fichero") + 1
                filename = " ".join(words[idx:])
        except:
            pass
        
        if not filename:
            self.speak("No entendí qué archivo quieres escanear. Dime: escanea el archivo nombre.extensión")
            return
        
        # Buscar archivo en ubicaciones comunes
        search_paths = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documentos"),
            os.path.expanduser("~/Escritorio"),
            os.getcwd()
        ]
        
        filepath = None
        for search_dir in search_paths:
            candidate = os.path.join(search_dir, filename)
            if os.path.exists(candidate):
                filepath = candidate
                break
        
        if not filepath:
            self.speak(f"No encontré el archivo {filename}")
            return
        
        self.speak(f"Escaneando {filename}...")
        is_infected, virus_name = self.virus_scanner.scan_file(filepath)
        
        if is_infected:
            self.speak(f"ALERTA: Virus {virus_name} detectado en {filename}. Moviendo a cuarentena.")
            self.virus_scanner.quarantine_file(filepath)
        else:
            self.speak(f"{filename} está limpio, no se detectaron amenazas.")
    
    def list_quarantine(self, command, response, **kwargs):
        """
        Lista archivos en cuarentena.
        Comando: "lista la cuarentena", "qué hay en cuarentena"
        """
        if not self.virus_scanner:
            self.speak("El sistema de cuarentena no está disponible.")
            return
        
        quarantined = self.virus_scanner.list_quarantine()
        
        if not quarantined:
            self.speak("No hay archivos en cuarentena.")
            return
        
        count = len(quarantined)
        names = ", ".join([q['filename'][:20] for q in quarantined[:3]])
        
        if count > 3:
            self.speak(f"Hay {count} archivos en cuarentena. Los primeros: {names}")
        else:
            self.speak(f"Archivos en cuarentena: {names}")
    
    def update_virus_signatures(self, command, response, **kwargs):
        """
        Actualiza base de datos de firmas de virus.
        Comando: "actualiza las firmas de virus", "actualiza antivirus"
        """
        if not self.virus_scanner or not self.virus_scanner.clamav_available:
            self.speak("ClamAV no está disponible.")
            return
        
        self.speak("Actualizando base de datos de virus, esto puede tardar...")
        
        success = self.virus_scanner.update_signatures()
        
        if success:
            self.speak("Firmas de virus actualizadas correctamente. Sistema protegido contra las últimas amenazas.")
        else:
            self.speak("No pude actualizar las firmas. Verifica tu conexión a internet y permisos sudo.")
    
    def security_status(self, command, response, **kwargs):
        """
        Informa estado del sistema de seguridad.
        Comando: "estado de seguridad", "cómo está la seguridad"
        """
        status = []
        
        # Check antivirus
        if self.virus_scanner and self.virus_scanner.clamav_available:
            status.append("Antivirus ClamAV activo")
        else:
            status.append("Antivirus no disponible")
        
        # Check WatermelonGuard
        if hasattr(self.core, 'guard') and self.core.guard and self.core.guard.running:
            status.append("Sistema de Detección de Intrusiones activo")
            sig_count = len(self.core.guard.signatures) if self.core.guard.signatures else 0
            status.append(f"{sig_count} firmas de ataque cargadas")
        else:
            status.append("Sistema de Detección inactivo")
        
        # Quarantine
        if self.virus_scanner:
            quarantined = len(self.virus_scanner.list_quarantine())
            if quarantined > 0:
                status.append(f"{quarantined} archivos en cuarentena")
        
        message = "Estado de Seguridad: " + ", ".join(status)
        self.speak(message)


# Función de registro para NeoCore
def load_skill(core):
    """Carga el skill de seguridad."""
    return SecuritySkill(core)
