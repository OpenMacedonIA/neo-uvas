from datetime import datetime
from . import BaseSkill

class SystemSkill(BaseSkill):
    def check_status(self, command, response, **kwargs):
        if self.core.sysadmin_manager:
            status = self.core.sysadmin_manager.get_full_status()
            
            # Add Battery if applicable
            battery = self.core.sysadmin_manager.get_battery_status()
            if battery != "No detectada":
                status += f" Batería al {battery}."
                
            self.speak(f"{response} {status}")
        else:
            self.speak("El módulo de administración no está disponible.")

    def list_services(self, command, response, **kwargs):
        """Lista los servicios activos."""
        if not self.core.sysadmin_manager:
            self.speak("No tengo permisos de administrador.")
            return

        self.speak(response)
        cmd = "systemctl list-units --type=service --state=running --no-pager --plain --no-legend"
        success, output = self.core.sysadmin_manager.run_command(cmd)
        
        if success:
            lines = output.strip().split('\n')
            count = len(lines)
            if count > 0:
                self.speak(f"Hay {count} servicios corriendo en este momento.")
                # Optional: Read first few? "Como ssh, docker..."
                # Extract names: 'service.name.service   loaded active running   Description'
                examples = []
                for line in lines[:3]:
                    parts = line.split()
                    if parts:
                        name = parts[0].replace('.service', '')
                        examples.append(name)
                
                if examples:
                    self.speak(f"Por ejemplo: {', '.join(examples)}.")
            else:
                self.speak("No encontré servicios activos (lo cual es raro).")
        else:
            self.speak("No pude listar los servicios.")

    def apagar(self, response, **kwargs):
        # Biometric Check (Alpha)
        if hasattr(self.core, 'biometrics_manager'):
            if self.core.biometrics_manager.is_voice_auth_enabled():
                self.speak("Verificando autorización por huella de voz...")
                # Simulate verification process
                if self.core.biometrics_manager.verify_voice(None):
                    self.speak("Identidad confirmada.")
                else:
                    self.speak("Acceso denegado. No reconozco tu voz.")
                    return

        self.speak(response)
        self.core.on_closing()

    def diagnostico(self, command, response, **kwargs):
        if self.core.sherlock:
            report = self.core.sherlock.run_diagnosis()
            if report:
                self.speak(f"{response} {report}")
            else:
                self.speak(f"{response} Todo parece estar en orden.")
        else:
            self.speak("Módulo Sherlock no disponible.")

    def queja_factura(self, command, response, **kwargs):
        self.speak(response)

    def restart_service(self, command, response, **kwargs):
        """Reinicia un servicio systemd especificado en el comando."""
        if not self.core.sysadmin_manager:
            self.speak("No tengo permisos de administrador.")
            return

        # Extraer nombre del servicio (simple heurística: última palabra o después de 'servicio')
        service_name = command.split("servicio")[-1].strip()
        if not service_name:
            self.speak("¿Qué servicio quieres que reinicie?")
            return

        self.speak(f"{response} {service_name}")
        success, msg = self.core.sysadmin_manager.control_service(service_name, "restart")
        if success:
            self.speak(f"Servicio {service_name} reiniciado correctamente.")
        else:
            self.speak(f"Error al reiniciar {service_name}: {msg}")

    def update_system(self, command, response, **kwargs):
        """Ejecuta apt update && upgrade."""
        if not self.core.sysadmin_manager:
            self.speak("No tengo permisos de administrador.")
            return

        self.speak(response)
        # Detectar OS para usar apt o dnf (aunque sysadmin.run_command es genérico, mejor ser específico)
        # Por ahora asumimos Debian/Ubuntu based en el roadmap
        cmd = "sudo apt-get update && sudo apt-get upgrade -y"
        
        # Ejecutar en background o esperar? Update tarda mucho.
        # Mejor lanzar y avisar.
        success, output = self.core.sysadmin_manager.run_command(cmd)
        if success:
            self.speak("Sistema actualizado. Revisa los logs si quieres detalles.")
        else:
            self.speak("Hubo un error en la actualización.")

    def find_file(self, command, response, **kwargs):
        """Busca un archivo usando 'find'."""
        if not self.core.sysadmin_manager:
            self.speak("No tengo acceso al sistema.")
            return

        # Heurística: "busca el archivo X en Y"
        parts = command.split(" en ")
        if len(parts) < 2:
            # Intenta buscar en todo el sistema si no se especifica ruta (peligroso/lento)
            # Mejor pedir ruta o asumir /home
            filename = command.replace("busca el archivo", "").replace("encuentra el archivo", "").strip()
            path = "/home"
        else:
            filename = parts[0].replace("busca el archivo", "").replace("encuentra el archivo", "").strip()
            path = parts[1].strip()

        self.speak(f"Buscando {filename} en {path}...")
        
        # Usar find
        cmd = f"find {path} -name '{filename}' 2>/dev/null | head -n 5"
        success, output = self.core.sysadmin_manager.run_command(cmd)
        
        if success and output.strip():
            lines = output.strip().split('\n')
            count = len(lines)
            self.speak(f"He encontrado {count} coincidencias. La primera es: {lines[0]}")
        else:
            self.speak("No he encontrado el archivo.")

    def give_morning_summary(self, command=None, response=None, **kwargs):
        """Ofrece un resumen matutino con el estado del sistema."""
        # 1. Saludo y Fecha
        now = datetime.now()
        fecha_str = now.strftime("%A %d de %B")
        summary = f"Buenos días. Hoy es {fecha_str}. "

        # 2. Estado del Sistema
        if self.core.sysadmin_manager:
            cpu = self.core.sysadmin_manager.get_cpu_usage()
            ram = self.core.sysadmin_manager.get_ram_usage()
            summary += f"El sistema está al {cpu}% de CPU y {ram}% de RAM. "
        
        # 3. Citas del día
        events = self.core.calendar_manager.get_events_for_day(now.year, now.month, now.day)
        if events:
            summary += f"Tienes {len(events)} eventos hoy. "
            first_event = events[0]
            summary += f"El primero es {first_event['description']} a las {first_event['time']}. "
        else:
            summary += "No tienes eventos en el calendario para hoy. "

        self.speak(summary)

    def check_service(self, command, response, **kwargs):
        """Verifica el estado de un servicio específico."""
        service = command.replace("estado del servicio", "").replace("cómo está el servicio", "").strip()
        if not service:
            self.speak("¿Qué servicio quieres comprobar?")
            return

        if self.core.sysadmin_manager:
            self.speak(response)
            active = self.core.sysadmin_manager.is_service_active(service)
            status = "activo" if active else "inactivo o no existe"
            self.speak(f"El servicio {service} está {status}.")
        else:
            self.speak("No tengo acceso al gestor de servicios.")

    def disk_usage(self, command, response, **kwargs):
        """Verifica el espacio en disco."""
        if self.core.sysadmin_manager:
            usage = self.core.sysadmin_manager.get_disk_usage() 
            self.speak(f"El uso del disco principal es del {usage} por ciento.")
            self.speak("No puedo leer el disco.")

    def system_info(self, command, response, **kwargs):
        """Información detallada del sistema (Kernel, Distro)."""
        if self.core.sysadmin_manager:
            info = self.core.sysadmin_manager.get_system_info()
            if info:
                text = f"Ejecutando {info.get('distro', 'Linux')} con kernel {info.get('release')}."
                text += f" Arquitectura {info.get('machine')}."
                self.speak(text)
            else:
                self.speak("No pude obtener la información del sistema.")
        else:
            self.speak("Módulo sysadmin no disponible.")

    def network_status(self, command, response, **kwargs):
        """Estado del tráfico de red."""
        if self.core.sysadmin_manager:
            sent, recv = self.core.sysadmin_manager.get_network_bytes()
            self.speak(f"Tráfico de red: {sent} enviados y {recv} recibidos.")
        else:
            self.speak("Módulo sysadmin no disponible.")
