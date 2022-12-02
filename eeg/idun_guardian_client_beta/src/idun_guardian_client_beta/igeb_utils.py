"""
Misc utility functions
"""

import random
import os
import platform
from Crypto.Cipher import ChaCha20_Poly1305
import numpy as np

# encryption configuration
KEY = bytes([i for i in range(32)])
NONCE = bytes([i for i in range(12)])
HEADER = b"IDUNIDUNIDUNIDUNIDUNIDUNIDUNIDUNc22"


def check_platform():
    """
    Check if the script is running on a cross platform

    Returns:
        bool: True if running on cross platform
    """
    if platform.system() == "Darwin":
        return "Darwin"
    elif platform.system() == "Linux":
        return "Linux"
    elif platform.system() == "Windows":
        return "Windows"
    else:
        raise Exception("Unsupported platform")


def check_valid_mac(mac_address: str) -> bool:
    """Check if mac address is valid

    Args:
        mac_address (str): Mac address

    Returns:
        bool: True if mac address is valid
    """
    if len(mac_address) != 17:
        return False
    if mac_address.count(":") != 5:
        return False
    print("Mac address is valid")
    return True


def check_valid_uuid(uuid: str) -> bool:
    """Check if uuid is valid

    Args:
        uuid (str): UUID
    """
    if len(uuid) != 36:
        return False
    if uuid.count("-") != 4:
        return False
    return True
