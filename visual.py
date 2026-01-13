from modules.skills import BaseSkill
import os

class VisualSkill(BaseSkill):
    def show_last_file(self, command, response, **kwargs):
        """Muestra el último archivo encontrado en la pantalla."""
        
        # 1. Recuperar contexto
        last_file = self.core.context.get('last_found_file')
        
        if not last_file:
            self.speak("No tengo ningún archivo en memoria para mostrar.")
            return

        if not os.path.exists(last_file):
            self.speak("El archivo que buscas ya no existe.")
            return

        # 2. Determinar tipo
        ext = last_file.split('.')[-1].lower()
        file_type = 'file'
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            file_type = 'image'
        elif ext in ['pdf', 'txt', 'md', 'html']:
            file_type = 'document'
        
        # 3. Construir URL (apunta al endpoint de WebAdmin)
        # Necesitamos la IP del servidor o path relativo si es el mismo origen.
        # Como el navegador carga la página desde el servidor, ruta relativa funciona.
        url = f"/api/visual/content?path={last_file}"
        
        self.speak(f"Mostrando {os.path.basename(last_file)} en pantalla.")
        
        # 4. Emitir evento al bus (WebAdmin -> Browser)
        # El evento debe ser 'visual:show' que el navegador escucha.
        # Pero WebAdmin es quien emite a SocketIO.
        # Necesitamos que WebService escuche este evento del bus y lo reenvíe.
        # O emitimos un evento genérico que WebService ya maneje.
        
        # Vamos a emitir un evento específico que WebService (wrapper) escuchará
        self.core.bus.emit('visual:show', {'url': url, 'type': file_type})

    def close_content(self, command, response, **kwargs):
        """Cierra el contenido visual."""
        self.speak("Cerrando visualización.")
        self.core.bus.emit('visual:close', {})
