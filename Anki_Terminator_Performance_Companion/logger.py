# addon/logger.py
import os
import queue
import threading
from datetime import datetime

class CompanionLogger:
    def __init__(self):
        self.logs = []
        self._callbacks = []
        
        # Path to companion.log inside the addon folder
        self.log_file_path = os.path.join(os.path.dirname(__file__), "companion.log")
        
        # Thread-safe queue for asynchronous disk logging
        self.log_queue = queue.Queue()
        
        # Start background worker thread to manage log file lifecycle without affecting UI
        self.log_thread = threading.Thread(target=self._log_worker, daemon=True)
        self.log_thread.start()

    def _log_worker(self):
        # Truncate/clear the log file instantly on startup
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            print(f"[Companion] Failed to truncate log file on startup: {e}")
            return

        # Continuous asynchronous write consumer loop
        while True:
            try:
                line = self.log_queue.get()
                if line == "__CLEAR__":
                    with open(self.log_file_path, "w", encoding="utf-8") as f:
                        f.write("")
                else:
                    with open(self.log_file_path, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                self.log_queue.task_done()
            except Exception as e:
                print(f"[Companion] Log file write error: {e}")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] {message}"
        self.logs.append(log_line)
        print(log_line)
        
        # Send to background thread for non-blocking file write
        self.log_queue.put(log_line)
        
        # Live trigger for GUI log updates
        for cb in self._callbacks:
            try:
                cb(log_line)
            except Exception:
                pass

    def get_logs(self):
        return "\n".join(self.logs)

    def clear(self):
        self.logs = []
        # Signal the background worker thread to clear the log file asynchronously
        self.log_queue.put("__CLEAR__")
        
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
