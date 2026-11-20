"""requirements.txt (hash-pinned, generated from requirements.in) must cover every package's needs.

The lock is how RedBlue installs where there is no network for package code (wheels downloaded by
hash, then the local packages installed editable with --no-deps --no-build-isolation). A dependency
added to a pyproject.toml but not to the lock would be missing there, so this fails first.
"""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIRS = sorted([*ROOT.joinpath("packages").iterdir(), ROOT / "admin"])


def _name(req: str) -> str:
    """The PEP 503 normalized project name of a requirement string."""
    m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req)
    assert m, f"unparseable requirement: {req!r}"
    return re.sub(r"[-_.]+", "-", m.group(1)).lower()


def _locked() -> dict[str, str]:
    text = ROOT.joinpath("requirements.txt").read_text(encoding="utf-8").replace("\\\n", " ")
    pins = {}
    for line in text.splitlines():
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if not line:
            continue
        m = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)", line)
        assert m, f"requirements.txt: not an exact pin: {line[:80]!r}"
        assert "--hash=sha256:" in line, f"requirements.txt: {m.group(1)} has no hash"
        pins[_name(m.group(1))] = m.group(2)
    return pins


def _pyprojects():
    for d in PACKAGE_DIRS:
        f = d / "pyproject.toml"
        if f.is_file():
            yield d.name, tomllib.loads(f.read_text(encoding="utf-8"))


def test_every_package_dependency_is_locked():
    locked = _locked()
    missing = [
        f"{pkg}: {dep}"
        for pkg, data in _pyprojects()
        for dep in data["project"].get("dependencies", [])
        if not _name(dep).startswith("redblue-") and _name(dep) not in locked
    ]
    assert not missing, (
        "add these to requirements.in and regenerate requirements.txt "
        f"(command at the top of requirements.in): {missing}"
    )


def test_every_build_backend_is_locked():
    locked = _locked()
    missing = [
        f"{pkg}: {req}"
        for pkg, data in _pyprojects()
        for req in data["build-system"]["requires"]
        if _name(req) not in locked
    ]
    assert not missing, f"local packages install without build isolation; lock: {missing}"


def test_no_local_package_is_locked_from_pypi():
    # The redblue-* distributions come from this repository. A pin would fetch a PyPI project of
    # the same name instead, which this repository does not control.
    assert not [n for n in _locked() if n.startswith("redblue")]


def test_the_lock_covers_every_package():
    names = {data["project"]["name"] for _, data in _pyprojects()}
    assert len(names) == 11, f"expected the 11 local packages, found {sorted(names)}"
