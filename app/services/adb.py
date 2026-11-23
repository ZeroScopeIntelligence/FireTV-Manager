from __future__ import annotations

import ipaddress
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


class ADBError(RuntimeError):
    """Raised when an ADB operation cannot be completed."""


class ADBService:
    def __init__(self, adb_path: str = "", timeout: int = 45):
        self.adb_path = adb_path.strip() or shutil.which("adb") or ""
        self.timeout = timeout

    def executable(self):
        candidate = self.adb_path or shutil.which("adb")
        if not candidate:
            raise ADBError(
                "ADB was not found. On Ubuntu/WSL install it with: sudo apt install adb"
            )
        if Path(candidate).exists():
            return candidate
        located = shutil.which(candidate)
        if located:
            return located
        raise ADBError(f"ADB executable does not exist: {candidate}")

    def run(self, args: list[str], timeout: int | None = None) -> str:
        try:
            result = subprocess.run(
                [self.executable(), *args],
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBError("ADB command timed out.") from exc
        except OSError as exc:
            raise ADBError(f"Could not start ADB: {exc}") from exc

        output = "\n".join(
            value for value in (result.stdout.strip(), result.stderr.strip()) if value
        )
        if result.returncode != 0:
            raise ADBError(output or f"ADB exited with code {result.returncode}")
        return output or "ADB command completed."

    def version(self) -> str:
        return self.run(["version"])

    def devices(self) -> str:
        return self.run(["devices", "-l"])

    def connect(self, ip: str, port: int = 5555) -> str:
        ipaddress.ip_address(ip)
        port = int(port)
        if not 1 <= port <= 65535:
            raise ADBError("Port must be between 1 and 65535.")
        return self.run(["connect", f"{ip}:{port}"])

    def install_apk(self, serial: str, apk_path: str, reinstall: bool = True) -> str:
        path = Path(apk_path).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".apk":
            raise ADBError("Choose an existing .apk file.")
        if not serial:
            raise ADBError("Select an authorized Fire TV device first.")
        args = ["-s", serial, "install"]
        if reinstall:
            args.append("-r")
        args.append(str(path))
        return self.run(args, timeout=180)

    def packages(self, serial: str) -> str:
        if not serial:
            raise ADBError("Select a connected Fire TV device first.")
        return self.run(
            ["-s", serial, "shell", "pm", "list", "packages", "-3"], timeout=60
        )

    def uninstall(self, serial: str, package_name: str) -> str:
        if not serial:
            raise ADBError("Select a connected Fire TV device first.")
        package_name = package_name.strip()
        if not package_name or any(char.isspace() for char in package_name):
            raise ADBError("Select a valid package name.")
        return self.run(["-s", serial, "uninstall", package_name], timeout=90)

    @staticmethod
    def _probe(ip: str, port: int, timeout: float) -> str | None:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return ip
        except OSError:
            return None

    def discover(
        self, cidr: str, port: int = 5555, timeout: float = 0.35,
        max_hosts: int = 512
    ) -> list[str]:
        try:
            network = ipaddress.ip_network(cidr.strip(), strict=False)
        except ValueError as exc:
            raise ADBError(f"Invalid subnet: {exc}") from exc
        if network.version != 4:
            raise ADBError("Enter an IPv4 subnet, such as 192.168.1.0/24.")
        hosts = list(network.hosts())
        if len(hosts) > max_hosts:
            raise ADBError(
                f"Subnet contains {len(hosts)} hosts. Use a smaller subnet "
                f"(maximum {max_hosts})."
            )
        found = []
        with ThreadPoolExecutor(max_workers=48) as pool:
            futures = [
                pool.submit(self._probe, str(host), int(port), timeout)
                for host in hosts
            ]
            for future in as_completed(futures):
                address = future.result()
                if address:
                    found.append(address)
        return sorted(found, key=lambda value: tuple(map(int, value.split("."))))
