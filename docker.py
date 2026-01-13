from . import BaseSkill
import logging
import json

class DockerSkill(BaseSkill):
    """
    Skill para la gestión de contenedores Docker.
    Integra MANGO T5 para la generación flexible de comandos.
    """
    def __init__(self, core):
        super().__init__(core)
        self.logger = logging.getLogger("DockerSkill")

    def consultar_estado(self, command, params, response):
        """Lista los contenedores activos usando MANGO T5 o fallback seguro."""
        
        # 1. Intentar inferencia si Mango está disponible
        cmd_to_run = None
        if hasattr(self.core, 'mango_manager') and self.core.mango_manager:
            mango_cmd, mango_conf = self.core.mango_manager.infer(command)
            if mango_cmd and mango_conf > 0.6:
                self.logger.info(f"MANGO (Docker Status) sugirió: {mango_cmd} ({mango_conf})")
                cmd_to_run = mango_cmd
        
        # 2. Fallback si no hay Mango o confianza baja
        if not cmd_to_run:
            cmd_to_run = "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"

        # 3. Ejecutar
        success, output = self.core.sysadmin_manager.run_command(cmd_to_run)
        
        if success:
            # Smart Filtering se encargará de resumirlo si es largo en NeoCore
            return f"Estado de contenedores ({cmd_to_run}):\n{output}"
        else:
            return f"Error ejecutando '{cmd_to_run}'. ¿Docker está corriendo?"

    def accion_contenedor(self, command, params, response):
        """
        Ejecuta una acción sobre un contenedor (start, stop, restart).
        Usa MANGO T5 para traducir la intención completa a un comando preciso.
        """
        # Intentamos usar MANGO primero para obtener el comando exacto
        # El input 'command' es la frase del usuario, ej: "Reinicia el contenedor pihole"
        
        # Opcional: Extraer nombre del parámetro si Padatious lo capturó
        container_name = params.get('container_name')
        
        # Pasamos la frase completa a MANGO
        mango_cmd, mango_conf = self.core.mango_manager.infer(command)
        
        if mango_cmd and mango_conf > 0.6 and "docker" in mango_cmd:
            self.logger.info(f"MANGO sugirió: {mango_cmd} (Conf: {mango_conf})")
            
            # Verificación de seguridad básica (whitelist dinámica)
            if any(x in mango_cmd for x in ['start', 'stop', 'restart', 'logs', 'ps']):
                 # Delegar al flujo de confirmación de NeoCore si es destructivo, 
                 # o ejecutar directo si es seguro?
                 # La implementación actual de NeoCore tiene un check de Mango en handle_command.
                 # PERO, como esto es una SKILL ejecutada por un INTENT, NeoCore ya delegó aquí.
                 # Debemos manejar la ejecución o confirmación nosotros mismos.
                 
                 # Si es una acción de modificación, confirmamos
                 self.core.pending_mango_command = mango_cmd
                 self.core.speak(f"Voy a ejecutar: {mango_cmd}. ¿Te parece bien?")
                 return # NeoCore manejará la respuesta sí/no en el siguiente turno
            else:
                self.core.speak("Mango ha generado un comando docker que no reconozco como seguro.")
        else:
            # Fallback manual si Mango falla (lógica "tonta")
            action = "restart" # Default
            if "parar" in command or "detener" in command: action = "stop"
            elif "iniciar" in command or "arrancar" in command: action = "start"
            
            if container_name:
                cmd = f"docker {action} {container_name}"
                self.core.pending_mango_command = cmd
                self.core.speak(f"No estoy seguro, pero creo que quieres ejecutar: {cmd}. ¿Correcto?")
            else:
                self.core.speak("No he entendido qué contenedor quieres tocar.")
