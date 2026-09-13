# A compose file that serves a finished folder over HTTP with nginx and a
# read-only mount.

import difflib
import json
import re
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

PARENT_MOUNT = "/srv/snapxo"
AUTH_LINES = ('\n    auth_basic "SnapXO archive";\n'
              "    auth_basic_user_file /etc/nginx/.htpasswd;\n")


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


def served_root(archive: Path) -> str:
    return f"{PARENT_MOUNT}/{archive.name}"


def build_nginx_conf(archive: Path, with_auth: bool) -> str:
    return (_template(NGINX_CONF_FILE)
            .replace("__ROOT__", served_root(archive))
            .replace("__AUTH__", AUTH_LINES if with_auth else ""))


def _volumes(archive: Path, with_auth: bool) -> list[str]:
    # The parent, not the archive: a bind mount pins the folder, a rename would go unseen.
    volumes = [f"{archive.parent.as_posix()}:{PARENT_MOUNT}:ro",
               "./snapxo.conf:/etc/nginx/conf.d/default.conf:ro"]
    if with_auth:
        volumes.append("./.htpasswd:/etc/nginx/.htpasswd:ro")
    return volumes


def build_compose(archive: Path, port: int, with_auth: bool) -> str:
    volumes = "\n".join(f"      - {json.dumps(volume)}" for volume in _volumes(archive, with_auth))
    return (_template(COMPOSE_FILE)
            .replace("__PORT__", str(port))
            .replace("__VOLUMES__", volumes)
            .rstrip("\n") + "\n")


def service_block(archive: Path, port: int, with_auth: bool) -> dict:
    volumes = _volumes(archive, with_auth)
    return {
        "image": "nginx:alpine",
        "container_name": SERVICE_NAME,
        "restart": "unless-stopped",
        "ports": [f"{port}:80"],
        "volumes": volumes,
    }


def _service_lines(archive: Path, port: int, with_auth: bool, indent: str = "  ") -> list[str]:
    # List items as JSON strings, valid YAML, so a path with spaces or colons stays one value.
    block = service_block(archive, port, with_auth)
    lines = [f"{indent}{SERVICE_NAME}:"]
    for key, value in block.items():
        if isinstance(value, list):
            lines.append(f"{indent * 2}{key}:")
            lines += [f"{indent * 3}- {json.dumps(item)}" for item in value]
        else:
            lines.append(f"{indent * 2}{key}: {value}")
    return lines


def _plain_service_yaml(archive: Path, port: int, with_auth: bool) -> str:
    return "\n".join(_service_lines(archive, port, with_auth))


def _is_top_level_key(line: str) -> bool:
    return bool(line.strip()) and not line[0].isspace() and not line.startswith("#")


def insert_service(text: str, archive: Path, port: int, with_auth: bool) -> str:
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"services:\s*(#.*)?$", line)), None)
    if start is None:
        if re.search(r"^services\s*:", text, re.MULTILINE):
            return text
        body = ["", "services:", *_service_lines(archive, port, with_auth)]
        return newline.join(lines + body) + newline

    end = next((i for i in range(start + 1, len(lines)) if _is_top_level_key(lines[i])), len(lines))
    children = [line for line in lines[start + 1:end] if line.strip() and not line.lstrip().startswith("#")]
    indent = children[0][:len(children[0]) - len(children[0].lstrip())] if children else "  "
    block = _service_lines(archive, port, with_auth, indent)

    existing = next((i for i in range(start + 1, end)
                     if re.match(rf"{indent}{SERVICE_NAME}:\s*(#.*)?$", lines[i])), None)
    if existing is not None:
        # Its body is everything indented deeper, comments included.
        stop = next((i for i in range(existing + 1, end)
                     if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= len(indent)), end)
        while stop > existing + 1 and not lines[stop - 1].strip():
            stop -= 1
        lines[existing:stop] = block
    else:
        at = end
        while at > start + 1 and not lines[at - 1].strip():
            at -= 1
        lines[at:at] = block
    return newline.join(lines) + newline


def _free_backup(path: Path) -> Path:
    # An identical backup is reused, a different one never overwritten.
    number = 1
    while True:
        candidate = path.with_name(path.name + (".bak" if number == 1 else f".bak.{number}"))
        if not candidate.exists() or candidate.read_bytes() == path.read_bytes():
            return candidate
        number += 1


def append_to_compose(existing: Path, archive: Path, port: int, with_auth: bool) -> bool:
    # Inserted as text, so comments and layout survive, then parsed to prove the result.
    try:
        import yaml
    except ImportError:
        console.print("[yellow]--append needs PyYAML, which is not installed "
                      "(pip install snapxo[docker]).[/yellow]")
        console.print("Add this service to your compose file by hand instead:\n")
        console.print(_plain_service_yaml(archive, port, with_auth), markup=False, highlight=False, soft_wrap=True)
        return False

    original = existing.read_bytes().decode("utf-8")
    try:
        document = yaml.safe_load(original) or {}
    except yaml.YAMLError as problem:
        console.print(f"[red]{existing} is not valid YAML: {problem}[/red]")
        return False
    if not isinstance(document, dict) or not isinstance(document.get("services") or {}, dict):
        console.print(f"[red]{existing} is not a compose file with a usable services section.[/red]")
        return False
    if SERVICE_NAME in (document.get("services") or {}):
        console.print(f"[yellow]{existing} already has a '{SERVICE_NAME}' service, replacing it.[/yellow]")

    updated = insert_service(original, archive, port, with_auth)
    expected = dict(document)
    expected["services"] = {**(document.get("services") or {}),
                            SERVICE_NAME: service_block(archive, port, with_auth)}
    try:
        matches = yaml.safe_load(updated) == expected
    except yaml.YAMLError:
        matches = False
    if not matches:
        console.print(f"[red]Could not add the service to {existing} without changing something else, "
                      f"so it was left as it is.[/red] Add this by hand under services:\n")
        console.print(_plain_service_yaml(archive, port, with_auth), markup=False, highlight=False, soft_wrap=True)
        return False

    backup = _free_backup(existing)
    shutil.copy2(existing, backup)
    existing.write_bytes(updated.encode("utf-8"))
    console.print(f"Added the '{SERVICE_NAME}' service to {existing}, the previous version is {backup.name}")
    diff = difflib.unified_diff(original.splitlines(), updated.splitlines(),
                                backup.name, existing.name, lineterm="")
    console.print("\n".join(diff), markup=False, highlight=False, soft_wrap=True)
    return True


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
    if archive.parent == archive or re.search(r'["$\\\n]', archive.name):
        console.print(f"[red]{archive} cannot be served: nginx needs a folder with a parent "
                      f"and a name without quotes, $ or backslashes.[/red]")
        return False
    with_auth = password is not None
    destination = compose_target(folder, target, append_to)

    if dry_run:
        console.print(f"Would write {destination} serving {archive} on port {port}")
        console.print(f"[yellow]The container would see everything in {archive.parent}.[/yellow]")
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

    (destination.parent / NGINX_CONF_FILE).write_text(build_nginx_conf(archive, with_auth), encoding="utf-8")
    console.print(f"Wrote {NGINX_CONF_FILE} next to it")
    console.print(f"[yellow]The container sees everything in {archive.parent}, read-only, so keep "
                  f"the archive in a folder of its own.[/yellow]")
    if with_auth:
        (destination.parent / HTPASSWD_FILE).write_text(credentials + "\n", encoding="utf-8")
        console.print(f"Wrote {HTPASSWD_FILE} next to it")
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
