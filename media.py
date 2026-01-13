from . import BaseSkill
import random

class MediaSkill(BaseSkill):
    def controlar_radio(self, command, response, **kwargs):
        if not self.core.player:
            self.speak("El módulo de radio no está disponible (falta VLC).")
            return

        # Buscar emisora en el comando
        emisora_encontrada = None
        for emisora in self.core.radios:
            if emisora['nombre'].lower() in command.lower():
                emisora_encontrada = emisora
                break
        
        if emisora_encontrada:
            self.speak(f"Poniendo {emisora_encontrada['nombre']}...")
            try:
                media = self.core.vlc_instance.media_new(emisora_encontrada['url'])
                self.core.player.set_media(media)
                self.core.player.play()
                self.core.event_queue.put({'type': 'speaker_status', 'status': 'busy'}) # Evitar que Neo se escuche a sí mismo
            except Exception as e:
                self.speak("Hubo un error al sintonizar la radio.")
                self.core.app_logger.error(f"Error VLC: {e}")
        else:
            nombres = ", ".join([e['nombre'] for e in self.core.radios])
            self.speak(f"No encuentro esa emisora. Tengo: {nombres}.")

            self.core.event_queue.put({'type': 'speaker_status', 'status': 'idle'})
            self.speak(response)

    def detener_radio(self, command, response, **kwargs):
        """Detiene la reproducción de la radio."""
        if self.core.player:
            self.core.player.stop()
            self.core.event_queue.put({'type': 'speaker_status', 'status': 'idle'})
            self.speak(response)
        else:
            self.speak("No hay radio reproduciéndose.")

    def cast_video(self, command, response, **kwargs):
        """
        Castea un vídeo a un dispositivo Chromecast.
        Comando esperado: "Pon el vídeo [URL/Nombre] en [Dispositivo]"
        """
        if not self.core.cast_manager:
            self.speak("El módulo de Chromecast no está disponible.")
            return

        parts = command.split(" en ")
        if len(parts) < 2:
            self.speak("Dime qué vídeo poner y en qué dispositivo. Ejemplo: Pon el vídeo de gatitos en la tele.")
            return

        # Simple parsing logic
        # "pon el vídeo X en Y" -> X is media, Y is device
        media_part = parts[0].replace("pon el vídeo", "").replace("pon un vídeo", "").strip()
        device_name = parts[1].strip()
        
        # For demo purposes, if media_part is not a URL, use a sample Big Buck Bunny
        media_url = media_part
        if not media_url.startswith("http"):
             # Sample video for testing
             media_url = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
             self.speak(f"Como no me has dado una URL, pondré Big Buck Bunny en {device_name}.")
        else:
             self.speak(f"{response} en {device_name}.")

        success, msg = self.core.cast_manager.play_media(device_name, media_url)
        self.speak(msg)

    def stop_cast(self, command, response, **kwargs):
        """Detiene la reproducción en Chromecast."""
        if not self.core.cast_manager:
            return

        # Check if a specific device is mentioned
        device_name = None
        # Heurística simple: si el comando contiene un nombre de dispositivo conocido
        known_devices = self.core.cast_manager.get_devices()
        for d in known_devices:
            if d.lower() in command.lower():
                device_name = d
                break
        
        success, msg = self.core.cast_manager.stop_media(device_name)
        self.speak(msg)
