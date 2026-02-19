import os
import logging
import logging.handlers
import sys
import sqlite3
import threading
import queue
import time
from datetime import datetime, timedelta
from pathlib import Path

def get_default_log_dir():
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "logs"

# --- 1. ASYNCHRÓNNY SQLITE HANDLER ---
class AsyncSQLiteHandler(logging.Handler):
    """
    Loguje do SQLite v samostatnom vlákne pomocou Queue.
    Nezaťažuje hlavné vlákno aplikácie I/O operáciami.
    """
    def __init__(self, db_path, retention_days=30):
        super().__init__()
        self.db_path = str(db_path)
        self.retention_days = int(retention_days)
        self.log_queue = queue.Queue()
        self.running = True
        
        # Inicializácia DB (synchrónne pri štarte)
        self._initialize_db()
        self._cleanup_old_logs()
        
        # Štart writera na pozadí
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name="LogWriter")
        self.writer_thread.start()

    def _initialize_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('PRAGMA journal_mode=WAL;') 
            conn.execute('PRAGMA synchronous=NORMAL;')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON logs (level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON logs (timestamp)')
            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"CRITICAL: DB Init Failed: {e}\n")

    def _cleanup_old_logs(self):
        if self.retention_days <= 0: return
        try:
            conn = sqlite3.connect(self.db_path)
            limit_date = datetime.now() - timedelta(days=self.retention_days)
            conn.execute("DELETE FROM logs WHERE timestamp < ?", (limit_date.strftime('%Y-%m-%d %H:%M:%S'),))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def emit(self, record):
        # Iba vložíme do fronty - toto je extrémne rýchle a neblokuje
        self.log_queue.put(record)

    def _writer_loop(self):
        """Slučka bežiaca na pozadí, ktorá vyberá logy z fronty a zapisuje ich v dávkach."""
        while self.running:
            try:
                record = self.log_queue.get(timeout=2.0)
            except queue.Empty:
                continue

            records_to_process = [record]
            
            try:
                while len(records_to_process) < 100: # Max dávka
                    records_to_process.append(self.log_queue.get_nowait())
            except queue.Empty:
                pass
            
            self._write_batch(records_to_process)
            
            for _ in records_to_process:
                self.log_queue.task_done()

    def _write_batch(self, records):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data = []
            for record in records:
                try:
                    module = record.name.split('.')[-1] if '.' in record.name else record.name
                    if module.startswith('utils.'): module = module.split('.')[-1]
                    ts = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    msg = record.getMessage()
                    data.append((ts, record.levelname, module, msg))
                except Exception:
                    pass # Chyba pri formátovaní logu
            
            if data:
                cursor.executemany('INSERT INTO logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)', data)
                conn.commit()
                
        except Exception as e:
            sys.stderr.write(f"Log DB Write Error: {e}\n")
        finally:
            if conn: conn.close()
            
    def close(self):
        self.running = False
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=1.0)
        super().close()

# --- 2. CONFIG HELPER ---

def setup_logging_from_config(config_dict):
    component_levels = config_dict.get('component_levels', {})
    
    logger = setup_logging(
        log_level=config_dict.get('log_level', logging.INFO),
        log_dir=config_dict.get('log_directory'),
        retention_days=config_dict.get('daily_backup_days', 30),
        console_colors=config_dict.get('console_colors', True),
        file_logging=config_dict.get('file_logging', True),
        console_logging=config_dict.get('console_logging', True)
    )
    
    _apply_component_log_levels(component_levels)
    return logger

def _apply_component_log_levels(component_levels):
    level_map = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR}
    
    default_levels = {
        'museum.main': 'INFO',
        'werkzeug': 'ERROR', 'flask.app': 'ERROR', 'urllib3': 'ERROR', 
        'paho': 'ERROR', 'socketio': 'ERROR', 'engineio': 'ERROR',
    }
    
    all_levels = default_levels.copy()
    for k, v in component_levels.items():
        all_levels[k.lower()] = v
    
    for logger_name, level_str in all_levels.items():
        logging.getLogger(logger_name).setLevel(level_map.get(level_str.upper(), logging.INFO))

def setup_logging(log_level=logging.INFO, log_dir=None, retention_days=30, console_colors=True,
                 file_logging=True, console_logging=False, **kwargs):
    
    class CleanFormatter(logging.Formatter):
        COLORS = {'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m', 'ERROR': '\033[31m', 'RESET': '\033[0m'}
        
        def format(self, record):
            module = record.name.split('.')[-1]
            if '.' in record.name: module = record.name.split('.')[-1]
            aliases = {'mqtt_client': 'mqtt', 'scene_parser': 'scene', 'web_dashboard': 'web'}
            module = aliases.get(module.lower(), module)[:10].ljust(10)
            
            ts = datetime.now().strftime('%H:%M:%S')
            msg = f"[{ts}] {record.levelname[:1]} {module} {record.getMessage()}"
            
            if console_colors and record.levelname in self.COLORS:
                return f"{self.COLORS[record.levelname]}{msg}{self.COLORS['RESET']}"
            return msg

    logger = logging.getLogger('museum')
    if logger.handlers: return logger
    
    logger.setLevel(log_level)
    logger.propagate = False
    
    if console_logging:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        ch.setFormatter(CleanFormatter())
        logger.addHandler(ch)
    
    if file_logging:
        log_dir = Path(log_dir) if log_dir else get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        try:
            db_path = log_dir / "museum_logs.db"
            # POUŽITIE NOVÉHO ASYNC HANDLERA
            sql_handler = AsyncSQLiteHandler(db_path, retention_days=retention_days)
            sql_handler.setLevel(logging.INFO)
            logger.addHandler(sql_handler)
            print(f"✅ Async DB Logging: Active (History: {retention_days} days)")
        except Exception as e:
            print(f"❌ DB Logging Failed: {e}")

        eh = logging.handlers.RotatingFileHandler(
            log_dir / 'museum-errors.log', maxBytes=1024*1024, backupCount=1, encoding='utf-8'
        )
        eh.setLevel(logging.ERROR)
        eh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        logger.addHandler(eh)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    return logger

def get_logger(name=None):
    if name: return logging.getLogger(f'museum.{name.lower()}')
    return logging.getLogger('museum')