class BaseSkill:
    def __init__(self, core):
        from modules.logger import app_logger
        self.core = core
        self.logger = app_logger

    def speak(self, text):
        self.core.event_queue.put({'type': 'speak', 'text': text})
