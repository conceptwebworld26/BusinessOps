"""Build the installable BusinessOps plugin from this development repository (ADR-0055).

This repository is the development source of truth: it holds the plugin together with its tests, evals,
development history, decision records and tooling. The package users install holds only what the plugin
needs at runtime. This script produces that package, with the plugin root at the package root, from an
explicit allowlist, so nothing developer-only can reach a user by accident and every runtime file is
copied from its single source here.

    python scripts/build_distribution.py [--out DIR]

`DIR` defaults to `dist/businessops` (ignored by git). An existing `DIR` is replaced only when it is a
previous build, identified by its `plugin.json` naming `businessops`; anything else is refused.

Transformations, the only ones:

- `.claude-plugin/plugin.json`: `experimental.evals` is removed, because `evals/` is not shipped and a
  manifest path that does not exist fails validation. Every other manifest field, `homepage` and
  `repository` included, is the source's: BusinessOps has one public repository, which holds both this
  source and the built package under `dist/businessops/`.
- `.claude-plugin/marketplace.json`: the plugin entry's `source` becomes `./`. In this repository the
  entry points at `./dist/businessops`, so `claude plugin marketplace add conceptwebworld26/BusinessOps`
  installs only the package (BOPS-R18); inside the package the plugin is the package root itself.
- Markdown files: a relative link to a file that is not shipped is rewritten to the same file in the
  development repository on GitHub, so documentation links keep working.

One file is generated rather than copied: a `.gitignore` at the package root, so Python bytecode written
when the plugin runs from that folder is never committed (BOPS-R16). It is repository hygiene only: no
plugin component reads it.

After building it checks the package and exits non-zero on any failure: a marketplace entry whose
`source` is not the package root, a manifest `icon` that is not an image file in the package, a `${CLAUDE_PLUGIN_ROOT}` path that does not exist, a forbidden path,
Python bytecode, a `.gitignore` other than the generated one, a file over 256 KiB, a binary file other
than an image, a symlink, more than 512 files, a relative Markdown link that does not resolve, or a personal machine path. It prints a JSON summary on stdout. Standard library only.
"""

import argparse
import io
import json
import os
import re
import shutil
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PLUGIN_NAME = "businessops"
REPOSITORY_URL = "https://github.com/conceptwebworld26/BusinessOps"
#: The package's marketplace entry `source`: the package root (BOPS-R18). This repository's entry is
#: `./dist/businessops`.
PACKAGE_PLUGIN_SOURCE = "./"
#: The package's `.gitignore` (BOPS-R16), generated into the package root. Narrow on purpose: it names
#: Python bytecode only, so it cannot hide a plugin file.
DISTRIBUTION_GITIGNORE = (
    "# Distribution-repository hygiene only; no BusinessOps component reads this file.\n"
    "# Python writes bytecode when the plugin runs from this folder. Never commit it.\n"
    "__pycache__/\n"
    "*.py[cod]\n"
)

#: Directories shipped whole (bytecode excluded).
SHIPPED_DIRS = ("agents", "commands", "config", "hooks", "lib", "reference", "skills")
#: Individual files shipped.
SHIPPED_FILES = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    # The directory-listing icon the manifest's `icon` names. Claude Code does not read it.
    ".claude-plugin/icon.svg",
    ".mcp.json",
    "README.md",
    "LICENSE",
    "EULA.md",
    "PRIVACY.md",
    "CONNECTORS.md",
    # The synthetic demo dataset, as text. The .xlsx copy is not shipped: it is a binary file and the
    # CSV holds the same data.
    "assets/demo-data/northwind_sales.csv",
    "assets/demo-data/business_context.json",
)
#: Paths that must never appear in the package.
FORBIDDEN = ("tests/", "evals/", "docs/", "dev/", "scripts/", ".claude/", "CLAUDE.md", "architecture.md",
             "project_plan.md", "assets/demo-data/generate_demo_data.py",
             "assets/demo-data/northwind_sales.xlsx")
#: Generated into the package, never copied from the development repository (whose `.gitignore` differs).
GENERATED_FILES = {".gitignore": DISTRIBUTION_GITIGNORE}
BYTECODE = re.compile(r"(^|/)__pycache__/|\.py[cod]$")

MAX_FILES = 512
MAX_FILE_BYTES = 256 * 1024
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
PERSONAL_PATH = re.compile(r"(/mnt/[a-z]/Prakash|[A-Za-z]:[\\/]+Prakash|Users[\\/]+Prakash)")
PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
MD_LINK = re.compile(r"(\]\()([^)\s#]+)((?:#[^)\s]*)?\))")


def _listing(rel_dir):
    out = []
    for directory, dirs, files in os.walk(os.path.join(REPO, rel_dir)):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(files):
            if name.endswith((".pyc", ".pyo")):
                continue
            path = os.path.join(directory, name)
            out.append(os.path.relpath(path, REPO).replace(os.sep, "/"))
    return out


def shipped_paths():
    """Every repository path the package contains, sorted."""
    paths = set(SHIPPED_FILES)
    for rel_dir in SHIPPED_DIRS:
        paths.update(_listing(rel_dir))
    return sorted(paths)


def _rewrite_links(text, rel_path, shipped):
    base = os.path.dirname(rel_path)

    def fix(match):
        target = match.group(2)
        if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("/"):
            return match.group(0)
        resolved = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
        if resolved in shipped or any(p.startswith(resolved.rstrip("/") + "/") for p in shipped):
            return match.group(0)
        kind = "tree" if os.path.isdir(os.path.join(REPO, resolved)) else "blob"
        return "%s%s/%s/main/%s%s" % (match.group(1), REPOSITORY_URL, kind, resolved, match.group(3))

    return MD_LINK.sub(fix, text)


def _transform(rel_path, data, shipped):
    if rel_path == ".claude-plugin/plugin.json":
        manifest = json.loads(data.decode("utf-8"))
        experimental = manifest.get("experimental")
        if isinstance(experimental, dict):
            experimental.pop("evals", None)
            if not experimental:
                del manifest["experimental"]
        return (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if rel_path == ".claude-plugin/marketplace.json":
        marketplace = json.loads(data.decode("utf-8"))
        for entry in marketplace["plugins"]:
            entry["source"] = PACKAGE_PLUGIN_SOURCE
        return (json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if rel_path.endswith(".md"):
        return _rewrite_links(data.decode("utf-8"), rel_path, shipped).encode("utf-8")
    return data


def _prepare(out):
    if not os.path.exists(out):
        return
    manifest = os.path.join(out, ".claude-plugin", "plugin.json")
    try:
        with io.open(manifest, encoding="utf-8") as handle:
            previous = json.load(handle).get("name")
    except (OSError, IOError, ValueError):
        previous = None
    if previous != PLUGIN_NAME:
        raise SystemExit("build_distribution: %s exists and is not a previous BusinessOps build; refusing to "
                         "replace it" % out)
    shutil.rmtree(out)


def check(out):
    """Every problem found in the package at `out`; an empty list means it passes."""
    problems, files = [], []
    for directory, dirs, names in os.walk(out):
        for name in dirs + names:
            if os.path.islink(os.path.join(directory, name)):
                problems.append("symlink: %s" % os.path.relpath(os.path.join(directory, name), out))
        for name in names:
            files.append(os.path.relpath(os.path.join(directory, name), out).replace(os.sep, "/"))
    shipped = set(files)
    try:
        with io.open(os.path.join(out, ".claude-plugin", "marketplace.json"), encoding="utf-8") as handle:
            sources = [entry.get("source") for entry in json.load(handle)["plugins"]]
    except (OSError, IOError, ValueError, KeyError, TypeError, AttributeError):
        sources = None
    if sources != [PACKAGE_PLUGIN_SOURCE]:
        problems.append("marketplace entry source is not the package root: %r" % (sources,))
    try:
        with io.open(os.path.join(out, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            icon = json.load(handle).get("icon")
    except (OSError, IOError, ValueError, AttributeError):
        icon = None
    # `claude plugin validate` does not check `icon`, so the package check does: the directory needs the file.
    if icon is not None:
        resolved = os.path.normpath(os.path.join(out, str(icon)))
        if (not str(icon).startswith("./") or not str(icon).lower().endswith(IMAGE_EXTENSIONS)
                or not resolved.startswith(os.path.normpath(out) + os.sep) or not os.path.isfile(resolved)):
            problems.append("manifest icon is not an image file in the package: %r" % (icon,))
    if len(files) > MAX_FILES:
        problems.append("%d files, over %d" % (len(files), MAX_FILES))
    for rel in files:
        path = os.path.join(out, rel)
        if any(rel == f or rel.startswith(f) for f in FORBIDDEN):
            problems.append("forbidden path: %s" % rel)
        if BYTECODE.search(rel):
            problems.append("python bytecode: %s" % rel)
        with io.open(path, "rb") as handle:
            data = handle.read()
        if rel in GENERATED_FILES and data != GENERATED_FILES[rel].encode("utf-8"):
            problems.append("not the generated file: %s" % rel)
        image = rel.lower().endswith(IMAGE_EXTENSIONS)
        if len(data) > MAX_FILE_BYTES and not image:
            problems.append("over 256 KiB: %s (%d bytes)" % (rel, len(data)))
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            if not image:
                problems.append("binary file: %s" % rel)
            continue
        if b"\x00" in data and not image:
            problems.append("binary file: %s" % rel)
        if PERSONAL_PATH.search(text):
            problems.append("personal machine path: %s" % rel)
        for ref in PLUGIN_ROOT_REF.findall(text):
            ref = ref.rstrip(".")
            if not os.path.exists(os.path.join(out, ref)):
                problems.append("missing ${CLAUDE_PLUGIN_ROOT}/%s (referenced in %s)" % (ref, rel))
        if rel.endswith(".md"):
            base = os.path.dirname(rel)
            for match in MD_LINK.finditer(text):
                target = match.group(2)
                if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("/"):
                    continue
                resolved = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
                if not os.path.exists(os.path.join(out, resolved)):
                    problems.append("broken link in %s: %s" % (rel, target))
    return sorted(set(problems)), files


def build(out):
    out = os.path.abspath(out)
    _prepare(out)
    paths = shipped_paths()
    shipped = set(paths)
    for rel in paths:
        source = os.path.join(REPO, rel)
        if not os.path.isfile(source):
            raise SystemExit("build_distribution: allowlisted file is missing: %s" % rel)
        with io.open(source, "rb") as handle:
            data = _transform(rel, handle.read(), shipped)
        target = os.path.join(out, rel)
        if not os.path.isdir(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        with io.open(target, "wb") as handle:
            handle.write(data)
    for rel, text in GENERATED_FILES.items():
        with io.open(os.path.join(out, rel), "wb") as handle:
            handle.write(text.encode("utf-8"))
    problems, files = check(out)
    size = sum(os.path.getsize(os.path.join(out, f)) for f in files)
    return {"package": out, "files": len(files), "bytes": size, "problems": problems}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.join(REPO, "dist", PLUGIN_NAME))
    args = parser.parse_args(argv)
    summary = build(args.out)
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    if summary["problems"]:
        sys.stderr.write("build_distribution: the package failed %d check(s)\n" % len(summary["problems"]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
