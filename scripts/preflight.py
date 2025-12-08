import sys
import os
import subprocess
from pathlib import Path

OK = "OK"
ERR = "ERROR"


def print_ok(msg: str) -> None:
    print(f"{OK}: {msg}")


def print_err(msg: str) -> None:
    print(f"{ERR}: {msg}")


def check_python() -> bool:
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 10):
        print_err(f"Python >= 3.10 required, found {ver.major}.{ver.minor}")
        return False
    print_ok(f"Python {ver.major}.{ver.minor}")
    return True


def check_ffmpeg() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        print_err("ffmpeg not found in PATH")
        return False
    except Exception as e:
        print_err(f"ffmpeg check failed: {e}")
        return False
    if r.returncode != 0:
        print_err(f"ffmpeg returned nonzero: {r.returncode}")
        return False
    first_line = (r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else ""
    if not first_line.lower().startswith("ffmpeg version"):
        print_err("Unable to parse ffmpeg version")
        return False
    print_ok(first_line.strip())
    return True


def check_moviepy() -> bool:
    try:
        import moviepy  # noqa: F401
    except Exception as e:
        print_err(f"moviepy import error: {e}")
        return False
    print_ok("moviepy import")
    return True


def check_output_dir() -> bool:
    out_dir = Path("scripts/_out")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        test_file = out_dir / ".preflight_write_test"
        test_file.write_text("ok")
        test_file.unlink()
    except Exception as e:
        print_err(f"Output dir not writable: {e}")
        return False
    print_ok(f"Writable: {out_dir}")
    return True


def main() -> int:
    checks = [
        ("python", check_python),
        ("ffmpeg", check_ffmpeg),
        ("moviepy", check_moviepy),
        ("output", check_output_dir),
        ]
    all_ok = True
    for name, fn in checks:
        ok = False
        try:
            ok = fn()
        except Exception as e:
            print_err(f"{name} check exception: {e}")
        all_ok = all_ok and ok
    if not all_ok:
        # Non-zero exit; caller scripts treat any non-zero as failure
        sys.exit(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
