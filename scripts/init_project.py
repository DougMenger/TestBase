"""Initialize a new project from this template (Windows).

    python scripts\\init_project.py [TARGET] [--skip-extension | --grid-only]

1. Copies the template (.claude, CLAUDE.md, claude-grid.json, ...) into TARGET.
2. Starts a git repo at TARGET with an initial commit (worktrees need one).
3. Builds and installs the "Claude Grid" VS Code extension (2x2 terminal grid).

Safe to rerun: existing files are never overwritten.
"""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent
TEMPLATE_ITEMS = [".claude", ".vscode", "scripts", "tools", "CLAUDE.md", "README.md", "SECURITY_AUDIT.md", "claude-grid.json", ".gitignore"]
GITIGNORE_LINES = [".claude/worktrees/", "*.vsix"]
EXTENSION_DIR = Path("tools") / "claude-grid"

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json"/>
  <Default Extension=".js" ContentType="application/javascript"/>
  <Default Extension=".md" ContentType="text/markdown"/>
  <Default Extension=".vsixmanifest" ContentType="text/xml"/>
</Types>
"""

VSIX_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="claude-grid" Version="0.1.0" Publisher="local"/>
    <DisplayName>Claude Grid</DisplayName>
    <Description xml:space="preserve">Open 4 Claude Code terminals in a 2x2 editor grid.</Description>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.85.0"/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
  </Assets>
</PackageManifest>
"""


def copy_template(target: Path) -> None:
    if target == TEMPLATE:
        return
    ignore = shutil.ignore_patterns("worktrees", "__pycache__", "*.vsix")

    def copy_if_missing(src, dst):
        if not Path(dst).exists():
            shutil.copy2(src, dst)

    for item in TEMPLATE_ITEMS:
        src = TEMPLATE / item
        if src.is_dir():
            shutil.copytree(src, target / item, ignore=ignore, copy_function=copy_if_missing, dirs_exist_ok=True)
        elif src.exists():
            copy_if_missing(src, target / item)
    print(f"Template copied to {target}")


def git(target: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=target, capture_output=True, text=True)


def init_git(target: Path) -> None:
    if not (target / ".git").exists():
        git(target, "init", "-b", "main")
        print("Initialized git repo")

    gitignore = target / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    missing = [line for line in GITIGNORE_LINES if line not in lines]
    if missing:
        gitignore.write_text("\n".join(lines + missing) + "\n")

    if git(target, "rev-parse", "--verify", "HEAD").returncode != 0:
        git(target, "add", "-A")
        result = git(target, "commit", "-m", "Initial commit")
        if result.returncode != 0:
            sys.exit(f"git commit failed (is user.name/user.email set?):\n{result.stderr}")
        print("Created initial commit")


def build_vsix(target: Path) -> Path:
    src = target / EXTENSION_DIR
    vsix = src / "claude-grid.vsix"
    with zipfile.ZipFile(vsix, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("extension.vsixmanifest", VSIX_MANIFEST)
        for f in src.iterdir():
            if f.is_file() and f.suffix != ".vsix":
                zf.write(f, f"extension/{f.name}")
    return vsix


def install_extension(target: Path) -> None:
    vsix = build_vsix(target)
    code = shutil.which("code")
    if not code:
        print(f"VS Code CLI 'code' not on PATH. Install manually: code --install-extension {vsix}")
        return
    subprocess.run([code, "--install-extension", str(vsix), "--force"], check=True)
    print("Installed Claude Grid extension. In VS Code: Ctrl+Shift+P -> 'Claude: Open 2x2 Terminal Grid'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=".", help="project folder (default: current folder)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--skip-extension", action="store_true", help="don't install the VS Code extension")
    group.add_argument("--grid-only", action="store_true", help="only (re)install the VS Code extension")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    if not args.grid_only:
        copy_template(target)
        init_git(target)
    if not args.skip_extension:
        install_extension(target)


if __name__ == "__main__":
    main()
