from . import BaseSkill
import random

class ContentSkill(BaseSkill):
    def contar_contenido_aleatorio(self, command, response, **kwargs):
        # Determinar tipo de contenido basado en el nombre del intent o comando
        # Pero aquí recibimos la función genérica.
        # En NeoCore original:
        # "contar_chiste": self.action_contar_contenido_aleatorio, 
        # "contar_dato_curioso": self.action_contar_contenido_aleatorio,
        
        # Necesitamos saber qué lista usar.
        # Podemos inferirlo del response o pasar un argumento extra si refactorizamos el mapa.
        # Por ahora, usaremos lógica simple basada en el comando o response.
        
        content_list = []
        if "chiste" in command or "broma" in command:
            content_list = self.core.chistes
        elif "dato" in command or "curiosidad" in command:
            content_list = self.core.datos_curiosos
            
        if content_list:
            item = random.choice(content_list)
            self.speak(f"{response} {item}")
        else:
            self.speak(response)

    def decir_frase_celebre(self, command, response, **kwargs):
        # Placeholder, no estaba implementado en NeoCore original con lista
        frases = ["El conocimiento es poder.", "Pienso, luego existo.", "A grandes males, grandes remedios."]
        self.speak(f"{response} {random.choice(frases)}")
        
    def aprender_alias(self, command, response, **kwargs):
        # "aprende que X es Y"
        parts = command.split(" es ")
        if len(parts) == 2:
            trigger = parts[0].replace("aprende que", "").strip()
            action_cmd = parts[1].strip()
            if self.core.brain:
                self.core.brain.learn_alias(trigger, action_cmd)
                self.speak(f"Entendido. He aprendido que '{trigger}' significa '{action_cmd}'.")
            else:
                self.speak("No tengo cerebro para aprender eso.")
        else:
            self.speak("No he entendido la estructura. Di 'aprende que X es Y'.")

    def aprender_dato(self, command, response, **kwargs):
        self.speak("Aún no sé aprender datos complejos, enséñame un alias mejor.")

    def consultar_dato(self, command, response, **kwargs):
        # Extraer el término a consultar
        # Heurística: "qué sabes de X", "dime qué es X"
        triggers = ["qué sabes de", "que sabes de", "recuerdas", "dime qué es", "dime que es"]
        query = command
        for t in triggers:
            if t in query:
                query = query.replace(t, "").strip()
                break
        
        if not query:
            self.speak("¿Qué quieres que consulte?")
            return

        if self.core.brain:
            results = self.core.brain.search_facts(query)
            if results:
                # Tomar el mejor resultado
                key, value = results[0]
                self.speak(f"{response} {value}")
            else:
                # Active Learning Trigger
                self.speak(f"No sé qué es {query}. ¿Dímelo tú y me lo guardo?")
                self.core.waiting_for_learning = query
        else:
            self.speak("No tengo cerebro conectado.")
