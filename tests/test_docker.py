# Docker is never run here, the compose file is generated and read back.

from pathlib import Path

import pytest
from click.testing import CliRunner

from snapxo.cli import main
from snapxo.formats.dockergen import (
    DEFAULT_PORT,
    NGINX_CONF_FILE,
    _template,
    build_compose,
    compose_command,
    compose_target,
    docker_htpasswd_command,
    service_block,
    write_compose,
)


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    folder = tmp_path / "archive"
    (folder / "_meta").mkdir(parents=True)
    (folder / "_meta" / "manifest.json").write_text('{"files": []}', encoding="utf-8")
    return folder


def test_the_archive_is_mounted_read_only(archive: Path):
    compose = build_compose(archive, 8080, with_auth=False)

    assert "/usr/share/nginx/html:ro" in compose
    assert '"8080:80"' in compose


def test_without_a_password_no_auth_files_are_mounted(archive: Path):
    compose = build_compose(archive, 8080, with_auth=False)

    assert ".htpasswd" not in compose
    assert "snapxo.conf" not in compose


def test_with_a_password_the_auth_files_are_mounted(archive: Path):
    compose = build_compose(archive, 8080, with_auth=True)

    assert "/etc/nginx/.htpasswd:ro" in compose
    assert "/etc/nginx/conf.d/default.conf:ro" in compose


def test_the_password_file_is_never_served():
    conf = _template(NGINX_CONF_FILE)

    assert "location ~ /\\. {\n        deny all;" in conf


def test_the_service_block_matches_the_template(archive: Path):
    block = service_block(archive, 9000, with_auth=False)

    assert block["image"] == "nginx:alpine"
    assert block["ports"] == ["9000:80"]
    assert block["volumes"][0].endswith(":/usr/share/nginx/html:ro")


def test_a_folder_snapxo_did_not_produce_is_refused(tmp_path: Path):
    stranger = tmp_path / "documents"
    stranger.mkdir()

    assert write_compose(stranger) is False
    assert not (stranger / "docker-compose.yml").exists()


def test_a_dry_run_writes_nothing(archive: Path):
    assert write_compose(archive, dry_run=True) is True
    assert not (archive / "docker-compose.yml").exists()


def test_the_compose_file_lands_next_to_the_archive(archive: Path):
    assert write_compose(archive) is True
    assert (archive / "docker-compose.yml").is_file()


def test_the_output_option_puts_it_somewhere_else(archive: Path, tmp_path: Path):
    elsewhere = tmp_path / "stacks"

    assert write_compose(archive, target=elsewhere) is True

    written = elsewhere / "docker-compose.yml"
    assert written.is_file()
    assert archive.resolve().as_posix() in written.read_text(encoding="utf-8")


def test_the_password_is_never_an_argument_value():
    # It would end up in shell history and in the process list.
    command = docker_htpasswd_command("hunter2")
    assert command[:4] == ["docker", "run", "--rm", "httpd:alpine"]
    assert "hunter2" in command  # only inside the container invocation, never in ours


def test_the_command_insists_on_a_choice_about_access(archive: Path):
    result = CliRunner().invoke(main, ["docker", str(archive)])

    assert result.exit_code == 1
    assert "--password" in result.output
    assert not (archive / "docker-compose.yml").exists()


def test_no_auth_serves_openly_after_saying_so(archive: Path):
    result = CliRunner().invoke(main, ["docker", str(archive), "--no-auth"])

    assert result.exit_code == 0
    assert (archive / "docker-compose.yml").is_file()


def test_asking_for_both_is_refused(archive: Path):
    result = CliRunner().invoke(main, ["docker", str(archive), "--no-auth", "--password"])

    assert result.exit_code == 1


def test_appending_keeps_an_existing_compose_file_valid(archive: Path, tmp_path: Path):
    yaml = pytest.importorskip("yaml")
    existing = tmp_path / "docker-compose.yml"
    existing.write_text("services:\n  other:\n    image: alpine\n", encoding="utf-8")

    assert write_compose(archive, append_to=existing) is True

    document = yaml.safe_load(existing.read_text(encoding="utf-8"))
    assert "other" in document["services"]
    assert document["services"]["snapxo"]["image"] == "nginx:alpine"


COMPOSE_WITH_COMMENTS = """\
# homelab stack, keep the order
services:
    traefik:
        image: traefik:v3  # pinned on purpose
#    wstunnel:
#        image: ghcr.io/erebe/wstunnel

volumes:
    data: {}
"""


def test_appending_keeps_comments_and_commented_out_services(archive: Path, tmp_path: Path, capsys):
    yaml = pytest.importorskip("yaml")
    existing = tmp_path / "docker-compose.yml"
    existing.write_text(COMPOSE_WITH_COMMENTS, encoding="utf-8")

    assert write_compose(archive, append_to=existing, port=9000) is True

    text = existing.read_text(encoding="utf-8")
    assert "# homelab stack, keep the order" in text
    assert "image: traefik:v3  # pinned on purpose" in text
    assert "#    wstunnel:\n#        image: ghcr.io/erebe/wstunnel" in text
    document = yaml.safe_load(text)
    assert list(document["services"]) == ["traefik", "snapxo"]
    assert document["volumes"] == {"data": {}}
    assert (tmp_path / "docker-compose.yml.bak").read_text(encoding="utf-8") == COMPOSE_WITH_COMMENTS
    assert '+        ports:' in capsys.readouterr().out


def test_appending_again_replaces_only_the_snapxo_service(archive: Path, tmp_path: Path):
    yaml = pytest.importorskip("yaml")
    existing = tmp_path / "docker-compose.yml"
    existing.write_text(COMPOSE_WITH_COMMENTS, encoding="utf-8")

    write_compose(archive, append_to=existing, port=9000)
    write_compose(archive, append_to=existing, port=9001)

    text = existing.read_text(encoding="utf-8")
    assert text.count("snapxo:") == 1
    assert yaml.safe_load(text)["services"]["snapxo"]["ports"] == ["9001:80"]
    assert "#    wstunnel:" in text
    # the first backup is the untouched original
    assert (tmp_path / "docker-compose.yml.bak").read_text(encoding="utf-8") == COMPOSE_WITH_COMMENTS
    assert (tmp_path / "docker-compose.yml.bak.2").is_file()


def test_a_file_it_cannot_edit_safely_is_left_alone(archive: Path, tmp_path: Path):
    pytest.importorskip("yaml")
    existing = tmp_path / "docker-compose.yml"
    existing.write_text("services: {other: {image: alpine}}\n", encoding="utf-8")

    assert write_compose(archive, append_to=existing) is False

    assert existing.read_text(encoding="utf-8") == "services: {other: {image: alpine}}\n"
    assert not (tmp_path / "docker-compose.yml.bak").exists()


def test_the_default_port_is_7627():
    assert DEFAULT_PORT == 7627


def test_output_names_a_directory_not_a_file(archive: Path, tmp_path: Path):
    elsewhere = tmp_path / "compose"
    elsewhere.mkdir()

    assert write_compose(archive, target=elsewhere) is True

    assert (elsewhere / "docker-compose.yml").is_file()
    assert not elsewhere.is_file()


def test_up_runs_where_the_compose_file_ended_up(archive: Path, tmp_path: Path):
    elsewhere = tmp_path / "compose"
    written = compose_target(archive, target=elsewhere)

    command = compose_command(written)

    assert str(elsewhere.resolve()) in command
    assert command[command.index("-f") + 1] == str(written)


def test_up_follows_an_appended_file_instead_of_the_archive(archive: Path, tmp_path: Path):
    existing = tmp_path / "homelab" / "docker-compose.yml"
    existing.parent.mkdir()

    written = compose_target(archive, append_to=existing)

    assert written == existing
    assert str(existing.parent) in compose_command(written)
