# addon/logger.py
from datetime import datetime

class CompanionLogger:
    def __init__(self):
        self.logs = []
        self._callbacks = []

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"
        self.logs.append(log_line)
        print(log_line)
        # Call active observers (like the Log Tab UI) to refresh live
        for cb in self._callbacks:
            try:
                cb(log_line)
            except Exception:
                pass

    def get_logs(self):
        return "\n".join(self.logs)

    def clear(self):
        self.logs = []
        for cb in self._callbacks:
            try:
                cb("")
            except Exception:
                pass

    def register_callback(self, cb):
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def unregister_callback(self, cb):
        if cb in self._callbacks:
            self._callbacks.remove(cb)

companion_logger = CompanionLogger()
