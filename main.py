import subprocess

# Example: Run the 'ls -l' command (Unix/Linux/macOS) or equivalent 'dir' (Windows)
# Use 'dir' on Windows, 'ls -l' on Unix
try:
    # For Unix-like systems (Linux, macOS)
    subprocess.run(["ls", "-l"])
except FileNotFoundError:
    # For Windows
    subprocess.run(["cmd", "/c", "dir"])
