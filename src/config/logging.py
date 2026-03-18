import logging
import sys
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from contextvars import ContextVar
 
# Context variable to track operation duration
operation_start: ContextVar[Optional[float]] = ContextVar('operation_start', default=None)
 
 
# ============================================================
# MODULE PREFIXES
# ============================================================
 
MODULE_PREFIXES = {
    'clients.cloudstack': '[CS]',
    'clients.keycloak': '[KC]',
    'adapters.cloudstack': '[CS-ADAPTER]',
    'adapters.keycloak': '[KC-ADAPTER]',
    'services.cloudstack': '[CS-SERVICE]',
    'services.keycloak': '[KC-SERVICE]',
    'webhook': '[WEBHOOK]',
    'provisioner': '[PROVISIONER]',
    'ks2cs': '[PROVISIONER]',
    'handlers': '[HANDLER]',
}
 
 
def get_prefix(logger_name: str) -> str:
    """Get prefix for logger based on module name."""
    for module, prefix in MODULE_PREFIXES.items():
        if logger_name.startswith(module):
            return prefix
    return '[APP]'
 
 
# ============================================================
# DURATION EXTRACTION
# ============================================================
 
def extract_duration_from_message(message: str) -> Tuple[str, Optional[float]]:
    """
    Extract duration from message if it ends with (XXms) or (XXs).
    
    Examples:
        "listAccounts OK (0.1858s)" → ("listAccounts OK", 185.8)
        "Create user failed (123ms)" → ("Create user failed", 123.0)
        "No duration here" → ("No duration here", None)
    """
    match = re.search(r'\s*\((\d+\.?\d*)(ms|s)\)\s*$', message)
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        
        # Convert to ms if needed
        if unit == 's':
            value = value * 1000
        
        # Remove the duration from message
        clean_message = message[:match.start()]
        return clean_message, value
    
    return message, None
 
 
# ============================================================
# CUSTOM LOG RECORD
# ============================================================
 
class EnhancedLogRecord(logging.LogRecord):
    """Enhanced LogRecord with prefix and duration extraction."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = get_prefix(self.name)
        self.duration_ms = None
        
        # Try to extract duration from message
        # (e.g., "listAccounts OK (0.1858s)" → extract 185.8ms)
        try:
            clean_msg, duration = extract_duration_from_message(self.getMessage())
            if duration:
                self.duration_ms = duration
                # Update message to clean version without duration
                self.msg = clean_msg
                self.args = ()  # Clear args since we modified msg
        except Exception:
            pass
        
        # Also check if we have a start time in context
        if not self.duration_ms:
            start_time = operation_start.get()
            if start_time:
                self.duration_ms = (time.time() - start_time) * 1000
 
 
# ============================================================
# COLORIZED FORMATTER
# ============================================================
 
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors, prefixes, and duration."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
    }
    RESET = '\033[0m'
    
    # Log level icons
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔴',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors, icons, and duration."""
        
        # Get icon and color
        icon = self.ICONS.get(record.levelname, '')
        color = self.COLORS.get(record.levelname, '')
        
        # Get prefix [CS], [KC], etc
        prefix = get_prefix(record.name)
        
        # Build duration string from message or context
        duration_str = ""
        if hasattr(record, 'duration_ms') and record.duration_ms:
            duration_str = f" ({record.duration_ms:.1f}ms)"
        
        # Formatted time
        formatted_time = self.formatTime(record, '%H:%M:%S')
        
        # Different format for DEBUG vs others
        if record.levelname == 'DEBUG':
            # DEBUG: Show file location AFTER prefix
            # [14:09:09] 🔍 [CS]  clients.cloudstack.base:42  Message (123.4ms)
            location = f"{record.name}:{record.lineno}"
            message = (
                f"{color}"
                f"[{formatted_time}] {icon} {prefix:16} {location:50}"
                f"{self.RESET} "
                f"{record.getMessage()}{duration_str}"
            )
        else:
            # INFO, WARNING, ERROR: Clean format with prefix always visible
            # [14:09:09] ✅ [CS]  Message (123.4ms)
            message = (
                f"{color}"
                f"[{formatted_time}] {icon} {prefix:16}"
                f"{self.RESET} "
                f"{record.getMessage()}{duration_str}"
            )
        
        return message
 
 
# ============================================================
# FILE FORMATTER
# ============================================================
 
class FileFormatter(logging.Formatter):
    """Detailed formatter for file output (no colors)."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for file."""
        
        # Get prefix
        prefix = get_prefix(record.name)
        
        # Build duration string
        duration_str = ""
        if hasattr(record, 'duration_ms') and record.duration_ms:
            duration_str = f" ({record.duration_ms:.1f}ms)"
        
        log_format = (
            "[%(asctime)s] %(levelname)-8s {prefix} "
            "%(name)s.%(funcName)s:%(lineno)d - %(message)s{duration_str}"
        ).format(prefix=prefix, duration_str=duration_str)
        
        formatter = logging.Formatter(
            log_format,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        return formatter.format(record)
 
 
# ============================================================
# SETUP LOGGING
# ============================================================
 
def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """
    Setup logging for entire application.
    
    Args:
        level: LOG level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to log to. Default: logs/cloudistack_YYYYMMDD.log
    
    Example:
        from config.logging import setup_logging
        
        setup_logging("DEBUG")  # Call FIRST, before other imports
    """
    
    # Create logs directory if not exists
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Default log file
    if log_file is None:
        log_file = log_dir / f"cloudistack_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_file = Path(log_file)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))
    
    # Use custom LogRecord class
    logging.setLogRecordFactory(EnhancedLogRecord)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # ====== CONSOLE HANDLER ======
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # ====== FILE HANDLER ======
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
    file_handler.setFormatter(FileFormatter())
    root_logger.addHandler(file_handler)
    
    # ====== SET CUSTOM LEVELS FOR MODULES ======
    
    # Our modules: DEBUG level (detailed)
    for module in ['clients', 'adapters', 'services', 'ks2cs', 'webhook', 'handlers']:
        logging.getLogger(module).setLevel(logging.DEBUG)
    
    # External libraries: WARNING level (less noise)
    for module in ['keycloak', 'urllib3', 'requests', 'cs']:
        logging.getLogger(module).setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(f"Logging initialized - Level: {level}, File: {log_file}")
 
 
# ============================================================
# HELPER: Start/End operation timing
# ============================================================
 
def start_operation() -> float:
    """Start timing an operation."""
    start_time = time.time()
    operation_start.set(start_time)
    return start_time
 
def end_operation(start_time: float) -> float:
    """Get duration of operation (in ms)."""
    duration = (time.time() - start_time) * 1000
    operation_start.set(None)
    return duration
 
# ============================================================
# DECORATOR: Automatic duration logging
# ============================================================
 
def log_duration(func):
    """Decorator to automatically log function duration."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            logger = logging.getLogger(func.__module__)
            logger.debug(f"{func.__name__}() completed in {duration:.1f}ms")
            
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__}() failed after {duration:.1f}ms: {e}")
            raise
    
    return wrapper
 
# Auto-initialize on import
if __name__ != "__main__":
    setup_logging()