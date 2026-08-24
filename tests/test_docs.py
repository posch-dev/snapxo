# The docs name flags and commands; this makes sure they still exist.

import re
from pathlib import Path

import pytest

from snapxo.cli import main

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DOCUMENTATION = ROOT / "DOCUMENTATION.md"
ALWAYS = {"--help", "--version", "--interactive"}


def every_real_flag() -> set[str]:
    flags = set(ALWAYS)
    for command in main.commands.values():
        for param in command.params:
            flags.update(opt for opt in param.opts + param.secondary_opts
                         if opt.startswith("-"))
    return flags


@pytest.mark.parametrize("doc", [README, DOCUMENTATION], ids=lambda path: path.name)
def test_no_doc_names_a_flag_that_is_gone(doc: Path):
    named = set(re.findall(r"(?<![\w-])--[a-z][a-z-]+", doc.read_text(encoding="utf-8")))

    missing = sorted(named - every_real_flag())
    assert not missing, f"{doc.name} names flags no command has: {missing}"


# The README is a quick guide and names only the commands worth starting with.
# DOCUMENTATION.md is the complete reference, so that is where every command
# has to appear.
def test_the_documentation_lists_every_command():
    text = DOCUMENTATION.read_text(encoding="utf-8")

    for name in main.commands:
        assert f"snapxo {name}" in text, name
