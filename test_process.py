#!/usr/bin/env python3

import psutil
import sys

def check_process(pid):
    try:
        p = psutil.Process(pid)
        print(f"Process {pid} exists: {p.is_running()}")
        print(f"Status: {p.status()}")
        print(f"Cmdline: {p.cmdline()}")
        return True
    except psutil.NoSuchProcess:
        print(f"Process {pid} not found")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pid = int(sys.argv[1])
        check_process(pid)
    else:
        print("Usage: python3 test_process.py <PID>")
