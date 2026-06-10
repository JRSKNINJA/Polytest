import logging
from datetime import datetime


class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.start_time = datetime.now()

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] {message}")
        self.logger.info(message)

    async def run(self) -> dict:
        raise NotImplementedError
