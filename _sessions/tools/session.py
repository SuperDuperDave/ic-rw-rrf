#!/usr/bin/env python3
"""Create concise research session notes or show read-only restart context.

Python 3.8+, standard library only. Paths are relative to this script, not cwd.
The complete stream filename is the identifier: concurrent different slugs may
share a sequence number, but exclusive creation never replaces an existing file.
"""

import argparse
from datetime import date
from pathlib import Path
import re
import subprocess
import sys


SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*", re.ASCII)
STREAM = re.compile(r"\d{4}-\d{2}-\d{2}-(\d{3})-[a-z0-9-]+\.md", re.ASCII)
CONTEXT_FILES = (
    ("Map", "_sessions/MAP.md"),
    ("Backlog", "_sessions/PLANNING.md"),
    ("Research state", "_sessions/RESEARCH_STATE.md"),
    ("Relay", "_sessions/RELAY.md"),
    ("Workflow", "_sessions/WORKFLOW.md"),
    ("Friction", "_sessions/FRICTION.md"),
)


def repository_root():
    return Path(__file__).resolve().parents[2]


def stream_paths(repo):
    """List names only; never load historical streams into context."""
    directory = repo / "_sessions" / "streams"
    return sorted(
        (path for path in directory.glob("*.md")
         if STREAM.fullmatch(path.name) and path.is_file()),
        reverse=True,
    )


def render_stream(day, sequence, slug, previous):
    previous_link = (
        "[{}]({})".format(previous.name, previous.name)
        if previous else "None yet."
    )
    return """# {day}-{sequence:03d} — {title}

Concise working notes: outcomes, evidence, decisions, and resume context.

## Resume
- Now: State the current objective and last verified result.
- Next: Name the smallest useful next action.
- In-flight: Record jobs, commands, output paths, and ownership; or none.

## Scope
- Intended outcome:
- Boundaries / constraints:

## Evidence and decisions log
- Append material changes with commands, artifact paths, results, and limitations.
- Separate observations from interpretations; link durable conclusions below.

## Hypotheses
- Claim / predicted observation / falsifier / test / outcome:

## Friction and noise log
- Obstacle / evidence / cost / next action or drop reason:

## Wrap pass
- SUBTRACT: Remove stale or duplicated context from active resume pointers.
- PROMOTE: Move reusable findings to durable docs and link the evidence.
- DROP: Close unhelpful paths with a brief reason; preserve the history.

## Carryforward pointers
- Previous stream: {previous}
- [Map](../MAP.md)
- [Planning / backlog](../PLANNING.md)
- [Research state](../RESEARCH_STATE.md)
- [Relay](../RELAY.md)
- [Friction](../FRICTION.md)
- Next session entry point:
""".format(day=day, sequence=sequence, title=slug.replace("-", " "),
           previous=previous_link)


def start_session(repo, slug, day=None):
    if len(slug) > 64 or not SLUG.fullmatch(slug):
        raise ValueError(
            "slug must be 1–64 lowercase ASCII letters/digits, separated by single hyphens"
        )
    day = date.today().isoformat() if day is None else day
    directory = repo / "_sessions" / "streams"
    directory.mkdir(parents=True, exist_ok=True)
    while True:
        paths = stream_paths(repo)
        sequence = 1 + max(
            (int(STREAM.fullmatch(path.name).group(1))
             for path in paths if path.name.startswith(day + "-")),
            default=0,
        )
        if sequence > 999:
            raise ValueError("all 999 session numbers for {} are in use".format(day))
        target = directory / "{}-{:03d}-{}.md".format(day, sequence, slug)
        content = render_stream(day, sequence, slug, paths[0] if paths else None)
        try:
            # Exclusive creation handles same-filename races and existing symlinks.
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
            return target
        except FileExistsError:
            # A colliding directory/symlink need not appear in stream_paths().
            # Report it instead of retrying forever; regular-file races rescan.
            if not target.is_file() or target.is_symlink():
                raise ValueError("stream path already occupied: {}".format(target))


def show_status(repo):
    print("Repository: {}".format(repo))
    print("Git branch and short status (including untracked paths):")
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo),
             "-c", "core.fsmonitor=false", "status", "--short", "--branch",
             "--untracked-files=normal"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", timeout=10, check=False,
        )
        if result.returncode == 0:
            print(result.stdout.rstrip() or "(clean)")
        else:
            detail = result.stderr.strip().splitlines()
            print("Unavailable: {}".format(detail[0] if detail else "git status failed"))
    except (OSError, subprocess.TimeoutExpired) as error:
        print("Unavailable: {}".format(error))

    print("Latest streams (up to 5):")
    latest = stream_paths(repo)[:5]
    for path in latest:
        print("  {}".format(path))
    if not latest:
        print("  (none)")
    print("Context files present:")
    present = [(label, repo / relative) for label, relative in CONTEXT_FILES
               if (repo / relative).is_file()]
    for label, path in present:
        print("  {}: {}".format(label, path))
    if not present:
        print("  (none)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="create a session stream using the local date")
    start.add_argument("slug", help="lowercase ASCII words separated by hyphens (max 64 characters)")
    commands.add_parser("status", help="show read-only repository restart context")
    args = parser.parse_args(argv)
    repo = repository_root()
    try:
        if args.command == "start":
            print(start_session(repo, args.slug))
        else:
            show_status(repo)
    except (OSError, ValueError) as error:
        parser.exit(1, "error: {}\n".format(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
