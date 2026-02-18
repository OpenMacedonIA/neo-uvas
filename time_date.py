from . import BaseSkill
from datetime import datetime
import locale

class TimeDateSkill(BaseSkill):
    def decir_hora_fecha(self, command, response, **kwargs):
        self.core.app_logger.info("TimeDateSkill: decir_hora_fecha executed.")
        now = datetime.now()
        # "Son las 18:30 del miércoles 25 de noviembre"
        try:
            fecha_str = now.strftime("Son las %H:%M del %A %d de %B.")
            self.speak(fecha_str)
        except Exception as e:
            self.core.app_logger.error(f"TimeDateSkill Error: {e}")
            self.speak(f"Son las {now.hour} y {now.minute}.")

    def decir_dia_semana(self, command, response, **kwargs):
        now = datetime.now()
        dia = now.strftime("%A")
        self.speak(f"{response} {dia}")
