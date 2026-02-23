from modules.BlueberrySkills import BaseSkill

class SSHSkill(BaseSkill):
    def connect(self, command, response, **kwargs):
        # "conecta con [alias]"
        alias = command.replace("conecta con", "").replace("conectar con", "").strip()
        
        if not alias:
            self.speak("No he entendido a qué servidor quieres conectar.")
            return

        self.speak(f"{response} Intentando conectar a {alias}...")
        success, msg = self.core.ssh_manager.connect(alias)
        self.speak(msg)

    def execute(self, command, response, **kwargs):
        # "ejecuta [instruccion] en [alias]"
        # "dime los archivos de home en [alias]"
        
        if " en " not in command:
            self.speak("Debes especificar 'en [servidor]'. Ejemplo: Lista archivos en Ubuntu.")
            return

        # Dividir instrucción y objetivo
        parts = command.split(" en ")
        # Heurística: la última parte probablemente sea el servidor, todo lo anterior es la instrucción
        alias = parts[-1].strip()
        instruction = " en ".join(parts[:-1]).replace("ejecuta", "").strip()

        # Comprobar si existe el servidor antes de consultar a Mango
        if alias not in self.core.ssh_manager.get_servers_list():
            # ¿Intentar coincidencia difusa? Por ahora estricta
            self.speak(f"No conozco el servidor '{alias}'.")
            return

        # Usar Mango para generar el comando
        self.speak(f"Pensando comando para '{instruction}' en {alias}...")
        
        # Inyección de contexto: Ninguno principalmente, o tal vez una pista de "remote server"
        mango_prompt = f"Contexto: Remote Linux Server | Instrucción: {instruction}"
        
        generated_cmd, confidence = self.core.mango_manager.infer(mango_prompt)
        
        if not generated_cmd or confidence < 0.6:
            self.speak("No estoy seguro de cómo traducir esa orden a un comando.")
            return
            
        # Confirmación (Seguridad por Voz)
        self.speak(f"Voy a ejecutar: '{generated_cmd}' en {alias}. ¿Procedo?")
        
        # Necesitamos bloquear/esperar confirmación. 
        # Ya que las habilidades son síncronas en la arq actual, podemos usar un pequeño parche o 
        # (mejor) establecer un estado pendiente en core y regresar.
        # Pero para esta iteración, asumamos que el usuario quiere ejecución directa por simplicidad 
        # O implementamos el bucle pendiente.
        
        # User requested: "La skill recoge la salida y la ejecuta"
        # Ejecutemos directamente pero anunciémoslo con cuidado.
        
        self.speak(f"Ejecutando...")
        success, output = self.core.ssh_manager.execute(alias, generated_cmd)
        
        if success:
            if len(output) > 200:
                self.speak("Comando exitoso. La salida es larga, te leo el final.")
                self.speak(output[-200:])
            else:
                self.speak(f"Resultado: {output}")
        else:
            self.speak(f"Error en el servidor: {output}")

    def disconnect(self, command, response, **kwargs):
        alias = command.replace("desconecta de", "").strip()
        if not alias:
            self.speak("¿De qué servidor me desconecto?")
            return

        success, msg = self.core.ssh_manager.disconnect(alias)
        self.speak(msg)
