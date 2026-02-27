"""
Logger Utility
Quản lý logging cho hệ thống
"""

import logging
import os
from datetime import datetime
from ..core.config import config


def setup_logger(
    name: str = "invoice_system",
    log_file: bool = True,
    console: bool = True
) -> logging.Logger:
    """
    Thiết lập logger
    
    Args:
        name: Tên logger
        log_file: Ghi vào file
        console: Hiển thị console
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Xóa handlers cũ
    logger.handlers = []
    
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        log_filename = os.path.join(
            config.LOG_DIR,
            f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "invoice_system") -> logging.Logger:
    """
    Lấy logger đã được thiết lập
    
    Args:
        name: Tên logger
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)