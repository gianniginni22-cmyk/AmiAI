"""Automatic Windows updater for Amigurumi AI.

Usage:
    AmigurumiAI-Updater.exe <installer_url> <sha256> <parent_pid>

The updater downloads the installer to %TEMP%, verifies SHA-256, waits for the
running Amigurumi AI process to terminate, then launches the installer.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

CHUNK = 1024 * 1024
LOG_PATH = os.path.join(tempfile.gettempdir(), "AmigurumiAI-updater.log")


def log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {message}\n")
    except Exception:
        pass


def download_and_verify(url, expected):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise RuntimeError("L'URL dell'installer deve usare HTTPS.")
    if len(expected) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected):
        raise RuntimeError("SHA-256 del manifest non valido.")

    log(f"Download start | url={url} | expected_sha256={expected}")
    fd, path = tempfile.mkstemp(prefix="AmigurumiAI-update-", suffix=".exe")
    os.close(fd)
    h = hashlib.sha256()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AmigurumiAI-Updater/0.7"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
            while True:
                block = r.read(CHUNK)
                if not block:
                    break
                f.write(block)
                h.update(block)
        got = h.hexdigest().lower()
        log(f"Download complete | sha256={got}")
        if got != expected.lower():
            log(f"SHA256 mismatch | got={got} | expected={expected}")
            raise RuntimeError(f"SHA256 non corrisponde: {got}")
        log(f"Verification OK | temp={path}")
        return path
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def wait_for_process(pid, timeout=60):
    """Wait for the parent process to exit, using a real Windows process handle."""
    if pid <= 0:
        return True

    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        SYNCHRONIZE = 0x00100000
        WAIT_OBJECT_0 = 0x00000000
        WAIT_TIMEOUT = 0x00000102
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
        if not handle:
            # The process may already have exited.
            return True
        try:
            result = kernel32.WaitForSingleObject(handle, int(timeout * 1000))
            if result == WAIT_OBJECT_0:
                return True
            if result == WAIT_TIMEOUT:
                raise RuntimeError("Timeout in attesa della chiusura di Amigurumi AI.")
            raise RuntimeError(f"WaitForSingleObject ha restituito {result}.")
        finally:
            kernel32.CloseHandle(handle)

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.2)
    raise RuntimeError("Timeout in attesa della chiusura di Amigurumi AI.")


def main():
    log(f"Start | argv_count={len(sys.argv)}")
    if len(sys.argv) < 4:
        log("Exit | insufficient arguments")
        return 2

    url, sha, pid_text = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        pid = int(pid_text)
    except ValueError:
        raise RuntimeError("PID del processo padre non valido.")

    log(f"Args OK | pid={pid}")
    installer = download_and_verify(url, sha)
    log(f"Installer ready | temp={installer}")
    wait_for_process(pid)
    log("Parent process exited")

    # Give Windows a short moment to release files held by the old process.
    time.sleep(0.5)
    subprocess.Popen([installer, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], close_fds=True)
    log(f"Installer launched | temp={installer}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"FATAL | {type(exc).__name__}: {exc}")
        raise SystemExit(1)
