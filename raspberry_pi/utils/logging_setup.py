import os
import logging
import logging.handlers
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

def get_default_log_dir():
    """Vráti predvolený adresár pre logy."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "logs"

# --- 1. SQLITE HANDLER (Prepojený na Config) ---
class SQLiteHandler(logging.Handler):
    """
    Ukladá logy do SQLite.
    retention_days: Počet dní, po ktorých sa staré logy zmažú (z configu).
    """
    def __init__(self, db_path, retention_days=30):
        super().__init__()
        self.db_path = str(db_path)
        self.retention_days = int(retention_days)
        self._initialize_db()
        self._cleanup_old_logs()

    def _initialize_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('PRAGMA journal_mode=WAL;') # Rýchly zápis
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
            # Indexy pre rýchle filtrovanie
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_level ON logs (level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON logs (timestamp)')
            
            conn.commit()
            conn.close()
        except Exception as e:
            sys.stderr.write(f"CRITICAL: DB Init Failed: {e}\n")

    def _cleanup_old_logs(self):
        """Vymaže logy staršie ako X dní (podľa configu)."""
        if self.retention_days <= 0:
            return # Ak je 0, nečisti nič (nekonečná história)

        try:
            conn = sqlite3.connect(self.db_path)
            limit_date = datetime.now() - timedelta(days=self.retention_days)
            limit_str = limit_date.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs WHERE timestamp < ?", (limit_str,))
            if cursor.rowcount > 0:
                print(f"🧹 Log Cleanup: Removed {cursor.rowcount} entries older than {self.retention_days} days.")
            
            conn.commit()
            conn.close()
        except Exception:
            pass

    def emit(self, record):
        try:
            # Čistý názov modulu
            module = record.name.split('.')[-1] if '.' in record.name else record.name
            if module.startswith('utils.'): module = module.split('.')[-1]
            
            ts = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO logs (timestamp, level, module, message) VALUES (?, ?, ?, ?)',
                         (ts, record.levelname, module, record.getMessage()))
            conn.commit()
            conn.close()
        except Exception:
            self.handleError(record)

# --- 2. PREPOJENIE S CONFIG MANAGEROM ---

def setup_logging_from_config(config_dict):
    """Tu sa 'prelievajú' nastavenia z config.ini do loggera."""
    component_levels = config_dict.get('component_levels', {})
    
    logger = setup_logging(
        log_level=config_dict.get('log_level', logging.INFO),
        log_dir=config_dict.get('log_directory'),
        # Tu sa prenáša nastavenie 'daily_backup_days' z configu do premennej retention_days
        retention_days=config_dict.get('daily_backup_days', 30),
        console_colors=config_dict.get('console_colors', True),
        file_logging=config_dict.get('file_logging', True),
        console_logging=config_dict.get('console_logging', True)
    )
    
    _apply_component_log_levels(component_levels)
    return logger

def _apply_component_log_levels(component_levels):
    """Nastaví levely pre konkrétne moduly podľa sekcie [LogLevels]."""
    level_map = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR}
    
    # Defaultné potlačenie ukecaných knižníc
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
        """Formátovač pre konzolu."""
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
    
    # 1. KONZOLA
    if console_logging:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        ch.setFormatter(CleanFormatter())
        logger.addHandler(ch)
    
    # 2. DB a SÚBOR
    if file_logging:
        log_dir = Path(log_dir) if log_dir else get_default_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        # A. SQLITE DATABÁZA (S dynamickým retention_days z configu)
        try:
            db_path = log_dir / "museum_logs.db"
            # Tu sa odovzdáva parameter z configu
            sql_handler = SQLiteHandler(db_path, retention_days=retention_days)
            sql_handler.setLevel(logging.INFO)
            logger.addHandler(sql_handler)
            print(f"✅ DB Logging: Active (History: {retention_days} days)")
        except Exception:
            print(f"❌ DB Logging: Failed")

        # B. LEN CHYBY DO SÚBORU
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