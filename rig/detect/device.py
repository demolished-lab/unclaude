"""Device detection — PRD FR-1.2, BLUEPRINT 2.

Stdlib-only, cross-platform. Returns budget + local model choice.
"""
import platform
import shutil

def detect():
    ram_gb = 16
    try:
        if platform.system() == "Windows":
            import ctypes
            class MEMSTAT(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            s = MEMSTAT()
            s.dwLength = ctypes.sizeof(MEMSTAT)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            ram_gb = round(s.ullTotalPhys / (1024**3))
        else:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_gb = round(int(line.split()[1]) / 1024 / 1024)
                        break
    except Exception:
        pass

    free_gb = 50
    try:
        free_gb = round(shutil.disk_usage("/").free / (1024**3)) if platform.system() != "Windows" else round(shutil.disk_usage("C:\\").free / (1024**3))
    except Exception:
        pass

    if ram_gb <= 12:
        budget, local = 1_500_000, "qwen2.5:0.5b"
    elif ram_gb >= 32:
        budget, local = 2_500_000, "qwen3:8b"
    else:
        budget, local = 2_000_000, "llama3.2:1b"

    return {"ram_gb": ram_gb, "free_gb": free_gb, "budget": budget, "local_model": local, "os": platform.system()}

if __name__ == "__main__":
    print(detect())
