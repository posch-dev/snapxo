# A compose file that serves a finished folder over HTTP with nginx and a
# read-only mount.

import shutil
import socket
import subprocess
from importlib import resources
from pathlib import Path

from rich.console import Console

from ..archive.manifest import load_manifest

console = Console()

COMPOSE_FILE = "docker-compose.yml"
HTPASSWD_FILE = ".htpasswd"
NGINX_CONF_FILE = "snapxo.conf"
DEFAULT_PORT = 7627  # SNAP on a phone keypad, and free on any normal machine
SERVICE_NAME = "snapxo"

AUTH_VOLUMES = ("      - ./snapxo.conf:/etc/nginx/conf.d/default.conf:ro\n"
                "      - ./.htpasswd:/etc/nginx/.htpasswd:ro")


def is_snapxo_folder(folder: Path) -> bool:
    return load_manifest(folder) is not None


def compose_target(folder: Path, target: Path | None = None,
                   append_to: Path | None = None) -> Path:
    # Its directory is what `./` in the compose file resolves against.
    if append_to is not None:
        return append_to
    return (target.resolve() / COMPOSE_FILE) if target else folder / COMPOSE_FILE


def _template(name: str) -> str:
    return resources.files("snapxo.templates").joinpath(name).read_text(encoding="utf-8")


def lan_address() -> str:
    # The address a phone can reach, which is never 127.0.0.1.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 1))  # reserved, never actually contacted
        return probe.getsockname()[0]
    except OSError:
        return "localhost"
    finally:
        probe.close()


def hash_password(password: str) -> str | None:
    # bcrypt when installed, otherwise the httpd image a Docker host already has.
    try:
        import bcrypt

        digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
        return f"{SERVICE_NAME}:{digest}"
    except ImportError:
        pass
    return _hash_password_with_docker(password)


def docker_htpasswd_command(password: str) -> list[str]:
    return ["docker", "run", "--rm", "httpd:alpine", "htpasswd", "-nbB", SERVICE_NAME, password]


def _hash_password_with_docker(password: str) -> str | None:
    if not shutil.which("docker"):
        return None
    try:
        result = subprocess.run(docker_htpasswd_command(password), capture_output=True,
                                text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    line = result.stdout.strip()
    return line if result.returncode == 0 and line.startswith(f"{SERVICE_NAME}:") else None


def build_compose(archive: Path, port: int, with_auth: bool) -> str:
    return (_template(COMPOSE_FILE)
            .replace("__PORT__", str(port))
            .replace("__ARCHIVE__", archive.as_posix())
            .replace("__AUTH_VOLUMES__", AUTH_VOLUMES if with_auth else "")
            .rstrip("\n") + "\n")


def service_block(archive: Path, port: int, with_auth: bool) -> dict:
    volumes = [f"{archive.as_posix()}:/usr/share/nginx/html:ro"]
    if with_auth:
        volumes.append("./snapxo.conf:/etc/nginx/conf.d/default.conf:ro")
        volumes.append("./.htpasswd:/etc/nginx/.htpasswd:ro")
    return {
        "image": "nginx:alpine",
        "container_name": SERVICE_NAME,
        "restart": "unless-stopped",
        "ports": [f"{port}:80"],
        "volumes": volumes,
    }


def append_to_compose(existing: Path, archive: Path, port: int, with_auth: bool) -> bool:
    # Never a text append: anchors and odd indentation would break the file.
    try:
        import yaml
    except ImportError:
        console.print("[yellow]--append needs PyYAML, which is not installed "
                      "(pip install snapxo[docker]).[/yellow]")
        console.print("Add this service to your compose file by hand instead:\n")
        console.print(_plain_service_yaml(archive, port, with_auth))
        return False

    document = yaml.safe_load(existing.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        console.print(f"[red]{existing} is not a compose file.[/red]")
        return False

    services = document.setdefault("services", {})
    if not isinstance(services, dict):
        console.print(f"[red]{existing} has no usable services section.[/red]")
        return False
    if SERVICE_NAME in services:
        console.print(f"[yellow]{existing} already has a '{SERVICE_NAME}' service, replacing it.[/yellow]")

    services[SERVICE_NAME] = service_block(archive, port, with_auth)
    existing.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    console.print(f"Added the '{SERVICE_NAME}' service to {existing}")
    return True


def _plain_service_yaml(archive: Path, port: int, with_auth: bool) -> str:
    lines = [f"  {SERVICE_NAME}:", "    image: nginx:alpine",
             f"    container_name: {SERVICE_NAME}", "    restart: unless-stopped",
             "    ports:", f'      - "{port}:80"', "    volumes:"]
    lines += [f"      - {volume}" for volume in service_block(archive, port, with_auth)["volumes"]]
    return "\n".join(lines)


def write_compose(
    folder: Path,
    target: Path | None = None,
    port: int = DEFAULT_PORT,
    password: str | None = None,
    append_to: Path | None = None,
    dry_run: bool = False,
) -> bool:
    if not is_snapxo_folder(folder):
        console.print(f"[red]{folder} has no _meta/manifest.json, so it is not a "
                      f"folder SnapXO produced. Refusing to serve it.[/red]")
        return False

    archive = folder.resolve()
    with_auth = password is not None
    destination = compose_target(folder, target, append_to)

    if dry_run:
        console.print(f"Would write {destination} serving {archive} on port {port}")
        return True

    credentials = None
    if with_auth:
        credentials = hash_password(password)
        if credentials is None:
            console.print("[red]Cannot hash the password: neither bcrypt nor Docker is "
                          "available. Install bcrypt with `pip install snapxo[docker]`.[/red]")
            return False

    destination.parent.mkdir(parents=True, exist_ok=True)
    if append_to is not None:
        if not append_to_compose(append_to, archive, port, with_auth):
            return False
    else:
        destination.write_text(build_compose(archive, port, with_auth), encoding="utf-8")
        console.print(f"Wrote {destination}")

    if with_auth:
        (destination.parent / NGINX_CONF_FILE).write_text(_template(NGINX_CONF_FILE), encoding="utf-8")
        (destination.parent / HTPASSWD_FILE).write_text(credentials + "\n", encoding="utf-8")
        console.print(f"Wrote {NGINX_CONF_FILE} and {HTPASSWD_FILE} next to it")
        console.print("[yellow]Basic auth over plain HTTP sends the password on every "
                      "request, only base64 encoded. Fine on your own network, not on "
                      "the open internet.[/yellow]")
    else:
        console.print("[yellow]No password: anyone who can reach this machine can read "
                      "the whole archive.[/yellow]")

    return True


def compose_command(compose_path: Path) -> list[str]:
    # Named, not left to whatever directory this was called from.
    return ["docker", "compose",
            "--project-directory", str(compose_path.parent),
            "-f", str(compose_path), "up", "-d"]


def compose_up(compose_path: Path, port: int) -> bool:
    if not shutil.which("docker"):
        console.print("[yellow]Docker is not on PATH, so the compose file was written "
                      "but not started.[/yellow]")
        return False
    result = subprocess.run(compose_command(compose_path))
    if result.returncode != 0:
        return False
    console.print(f"Running on http://{lan_address()}:{port} and http://localhost:{port}")
    return True
