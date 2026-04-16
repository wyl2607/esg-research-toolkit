"""Shared slowapi limiter instance — import from here to avoid circular imports."""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

default_limits = [] if os.getenv("ESG_CONTRACT_TEST_MODE") == "1" else ["60/minute"]

limiter = Limiter(key_func=get_remote_address, default_limits=default_limits)
