"""Windows drive enumeration (drive letters, drive type, mapped-network-drive targets) via the Win32 API (ctypes)."""
import os
import string

DRIVE_TYPES = {2: "removable", 3: "fixed", 4: "network", 5: "optical", 6: "ramdisk"}


def _mapped_target(letter: str) -> str | None:
    import ctypes
    from ctypes import wintypes

    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(len(buf))
    rc = ctypes.windll.mpr.WNetGetConnectionW(f"{letter}:", buf, ctypes.byref(size))
    return buf.value if rc == 0 else None


def list_windows_drives() -> list[dict]:
    """[{'path': 'C:\\', 'type': 'fixed', 'target': None}, {'path': 'Z:\\', 'type': 'network', 'target': '\\\\NAS\\Media'}]"""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        mask = kernel32.GetLogicalDrives()
        drives = []
        for i, letter in enumerate(string.ascii_uppercase):
            if not mask & (1 << i):
                continue
            root = f"{letter}:\\"
            dtype = DRIVE_TYPES.get(kernel32.GetDriveTypeW(root), "unknown")
            target = _mapped_target(letter) if dtype == "network" else None
            drives.append({"path": root, "type": dtype, "target": target})
        return drives
    except (AttributeError, OSError):
        letters = os.listdrives() if hasattr(os, "listdrives") else [
            f"{c}:\\" for c in string.ascii_uppercase if os.path.exists(f"{c}:\\")]
        return [{"path": d, "type": "unknown", "target": None} for d in letters]
