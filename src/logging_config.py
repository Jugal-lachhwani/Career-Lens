"""
Logging Configuration Module.

This module provides centralized logging configuration for the entire
Job Search Agent application. It sets up loggers with appropriate
formatters and handlers.
"""

import logging
import sys
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_file: str = None,
    console_output: bool = True
):
    """
    Configure application-wide logging.
    
    Sets up logging with both console and file handlers, with customizable
    log levels and output destinations.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to INFO.
        log_file (str, optional): Path to log file. If None, file logging is disabled.
        console_output (bool): Whether to output logs to console. Defaults to True.
        
    Example:
        >>> setup_logging(log_level="DEBUG", log_file="app.log")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        root_logger.info(f"Logging to file: {log_file}")
    
    root_logger.info(f"Logging initialized at level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name (str): Name of the module (typically __name__).
        
    Returns:
        logging.Logger: Configured logger instance.
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    return logging.getLogger(name)


# Configure default logging on module import
if not logging.getLogger().handlers:
    setup_logging(log_level="INFO", console_output=True)
