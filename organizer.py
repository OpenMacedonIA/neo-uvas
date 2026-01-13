from . import BaseSkill
from modules.date_parser import parse_reminder_from_text, parse_alarm_from_text

class OrganizerSkill(BaseSkill):
    def crear_recordatorio_voz(self, command, response, **kwargs):
        for trigger in ["recuérdame que", "recuerdame que", "recuérdame el", "recuerdame el", "añade un recordatorio"]:
            if command.startswith(trigger):
                reminder_text = command[len(trigger):].strip()
                break
        else:
            reminder_text = command

        parsed_data = parse_reminder_from_text(reminder_text)

        if not parsed_data:
            self.speak("No he podido entender la descripción del recordatorio.")
            return

        if parsed_data.get("status") == "needs_date":
            self.core.waiting_for_reminder_date = True
            self.core.pending_reminder_description = parsed_data['description']
            self.speak(f"Claro, ¿para cuándo quieres que te recuerde '{self.core.pending_reminder_description}'?")
        else:
            self.core.pending_reminder_data = parsed_data
            self.core.waiting_for_reminder_confirmation = True
            
            if parsed_data.get("time_inferred", False):
                self.core.pending_reminder_data["time"] = "09:00"
                feedback_hora = "a las 9 de la mañana"
            else:
                feedback_hora = f"a las {parsed_data['time']}"

            confirm_text = f"He entendido: recordatorio para {parsed_data['description']} el día {parsed_data['date']} {feedback_hora}. ¿Es correcto?"
            self.speak(confirm_text)

    def crear_alarma_voz(self, command, response, **kwargs):
        parsed_data = parse_alarm_from_text(command)
    
        if parsed_data:
            self.core.pending_alarm_data = parsed_data
            self.core.waiting_for_alarm_confirmation = True
    
            hour, minute = parsed_data['time']
            days = parsed_data['days']
            
            days_str_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
            if len(days) == 7 or not days: 
                days_text = "todos los días"
            else:
                days_text = "los " + ", ".join([days_str_map[d] for d in sorted(days)])
            
            confirm_text = f"Entendido. Voy a programar una alarma para las {hour:02d}:{minute:02d} {days_text}. ¿Es correcto?"
            self.speak(confirm_text)
        else:
            self.speak("No he podido entender la hora de la alarma.")

    def consultar_recordatorios_dia(self, command, response, **kwargs):
        # Placeholder implementation
        self.speak("Aquí tienes tus recordatorios (simulado).")

    def consultar_alarmas(self, command, response, **kwargs):
        alarms = self.core.alarm_manager.get_active_alarms()
        if alarms:
            self.speak(f"Tienes {len(alarms)} alarmas activas.")
        else:
            self.speak("No tienes alarmas activas.")

    def iniciar_dialogo_temporizador(self, command, response, **kwargs):
        self.core.waiting_for_timer_duration = True
        self.speak(response)

    def consultar_temporizador(self, command, response, **kwargs):
        if self.core.active_timer_end_time:
            import time
            from datetime import datetime
            remaining = int((self.core.active_timer_end_time - datetime.now()).total_seconds())
            if remaining > 60:
                self.speak(f"Quedan {remaining // 60} minutos.")
            else:
                self.speak(f"Quedan {remaining} segundos.")
        else:
            self.speak("No hay ningún temporizador activo.")

    def crear_temporizador_directo(self, command, response, **kwargs):
        # "Pon un temporizador de X minutos"
        # Parseo simple
        import re
        from datetime import datetime, timedelta
        
        minutes = 0
        match = re.search(r'(\d+)\s*minuto', command)
        if match:
            minutes = int(match.group(1))
            
        if minutes > 0:
            self.core.active_timer_end_time = datetime.now() + timedelta(minutes=minutes)
            self.speak(f"Temporizador de {minutes} minutos iniciado.")
        else:
            self.speak("No entendí de cuánto tiempo.")

    def consultar_citas(self, command, response, **kwargs):
        """Consulta citas para hoy."""
        from datetime import date
        today = date.today()
        # Access calendar_manager via core
        if hasattr(self.core, 'calendar_manager'):
            events = self.core.calendar_manager.get_events_for_day(today.year, today.month, today.day)
            
            if events:
                msg = f"Tienes {len(events)} citas para hoy: "
                for event in events:
                    msg += f"a las {event['time']}, {event['description']}. "
                self.speak(msg)
            else:
                self.speak("No tienes citas para hoy.")
        else:
            self.speak("El gestor de calendario no está disponible.")
