"""Pytest conftest — suppress bytecode and cache artifacts.

Đặt file này ở root repo. Pytest load conftest trước khi import test modules,
nên `sys.dont_write_bytecode = True` sẽ áp dụng cho toàn bộ session test.
"""
import os
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
