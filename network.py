from . import BaseSkill

class NetworkSkill(BaseSkill):
    def scan(self, command, response, **kwargs):
        if self.core.network_manager:
            # self.speak("Iniciando escaneo de red, dame unos segundos...")
            res = self.core.network_manager.scan_network()
            return f"Escaneo completado: {res}"
        else:
            return "Error: Módulo de red no disponible."

    def ping(self, command, response, **kwargs):
        # Limpieza fonética para cuando entiende "pink" o "pin"
        target = command.lower()
        for prefix in ["haz un ping a", "ping a", "pink a", "pin a", "latencia con"]:
            target = target.replace(prefix, "")
        
        target = target.strip()
        
        if not target:
            return "No especificaste a qué hacer ping."
            
        # Check for aliases
        try:
            skills_config = self.core.skills_config
            if skills_config:
                network_config = skills_config.get('network', {}).get('config', {})
                aliases = network_config.get('aliases', {})
                if target in aliases:
                    target = aliases[target]
                    # self.speak(f"Haciendo ping a {target}")
        except Exception as e:
            self.core.app_logger.error(f"Error checking aliases: {e}")
            
        if self.core.network_manager:
            res = self.core.network_manager.ping_host(target)
            return res
        else:
            return "Error: Módulo de red no disponible."

    def whois(self, command, response, **kwargs):
        target = command.replace("whois a", "").replace("haz un whois a", "").strip()
        if self.core.network_manager:
            res = self.core.network_manager.whois_lookup(target)
            return res
        else:
            return "Error: Módulo de red no disponible."
            
    def public_ip(self, command, response, **kwargs):
        """Obtiene la IP pública usando un servicio externo."""
        import requests
        try:
            self.speak(response)
            ip = requests.get('https://api.ipify.org').text
            self.speak(f"Tu IP pública es {ip}")
        except Exception as e:
            self.speak("No pude obtener la IP pública. Verifica tu conexión.")
            self.core.app_logger.error(f"Error public_ip: {e}")

    def escalar_cluster(self, command, response, **kwargs):
        self.speak(response)

    def speedtest(self, command, response, **kwargs):
        """Ejecuta un test de velocidad."""
        if self.core.sysadmin_manager:
            self.speak(response)
            res = self.core.sysadmin_manager.run_speedtest()
            if "error" in res:
                self.speak(f"Hubo un error: {res['error']}")
            else:
                self.speak(f"Test completado. Bajada: {res['download']}. Subida: {res['upload']}. Ping: {res['ping']}.")
        else:
            self.speak("No tengo acceso al módulo de administración.")
