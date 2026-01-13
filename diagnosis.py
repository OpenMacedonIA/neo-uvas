import os
import re
from . import BaseSkill

class DiagnosisSkill(BaseSkill):
    """
    Skill de Auto-Diagnóstico Avanzado.
    Analiza logs del sistema y utiliza el motor de IA para explicar errores y proponer soluciones.
    """

    def __init__(self, core=None):
        super().__init__(core)
        self.log_file = "logs/app.log" 

    def realizar_diagnostico(self, command, response, **kwargs):
        """
        Punto de entrada principal para la intención 'realizar_diagnostico'.
        """
        self.speak("Iniciando diagnóstico del sistema. Dame un segundo para leer los registros...")
        
        # 1. Escanear logs
        errors = self._scan_logs_for_errors(lines=50)
        
        if not errors:
            self.speak("He revisado los últimos registros y no veo errores críticos recientes. Todo parece normal.")
            return

        # 2. Analizar el primer error crítico encontrado (para no saturar)
        first_error = errors[0]
        self.speak(f"He encontrado un error reciente relacionado con: {first_error['summary']}")
        
        # 3. Consultar al Motor de IA para diagnóstico y solución
        if self.core.ai_engine:
            analysis = self._analyze_with_ai(first_error['full_text'])
            self.speak(analysis)
        else:
            self.speak(f"El error dice: {first_error['summary']}. Te sugiero revisar el log manualmente.")

    def _scan_logs_for_errors(self, lines=50):
        """Lee las últimas N líneas y busca patrones de error/critical."""
        found_errors = []
        try:
            if not os.path.exists(self.log_file):
                return []

            with open(self.log_file, 'r') as f:
                # Leer últimas lineas
                # Forma eficiente para archivos grandes: seek al final y leer bloques hacia atrás
                # Simplificación: leer todo si no es gigante, o usar deque
                from collections import deque
                last_lines = deque(f, maxlen=lines)
                
                for line in last_lines:
                    if "ERROR" in line or "CRITICAL" in line or "Exception" in line:
                        # Limpiar timestamp para el resumen
                        parts = line.split(" - ")
                        summary = parts[-1].strip() if len(parts) > 1 else line.strip()
                        
                        found_errors.append({
                            'full_text': line.strip(),
                            'summary': summary[:100] # Primeros 100 chars
                        })
        except Exception as e:
            print(f"Error scanning logs: {e}")
            
        return found_errors

    def _analyze_with_ai(self, error_text):
        """
        Usa Gemma/LLM para generar una explicación amigable y una propuesta de solución.
        """
        prompt = (
            f"Actúa como un ingeniero de sistemas experto. Analiza el siguiente error de log:\n"
            f"'{error_text}'\n"
            f"1. Explica brevemente qué pasó (en español sencillo).\n"
            f"2. Propón una solución técnica concreta (comando o cambio de config) pero NO la ejecutes.\n"
            f"Respuesta muy concisa (máximo 2 frases)."
        )
        
        # Usamos el chat manager o ai_engine directamente
        try:
            response = self.core.ai_engine.generate(prompt, max_length=150)
            return response
        except Exception:
            return "No he podido generar un diagnóstico detallado, pero el error parece importante."
