#!/usr/bin/env python3
"""Use this project's installed Relay, or start Claude with its Relay hooks.

Usage: relay.py <relay arguments...>
       relay.py claude-plan
       relay.py claude <native Claude arguments...>

Python 3.8+, standard library only. No installation, enrollment, trust changes,
or persistent provider settings are performed automatically. Executable paths
may be overridden with IC_RRF_RELAY_BIN and IC_RRF_CLAUDE_BIN.
"""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys


class Interrupted(Exception):
    def __init__(self, signum):
        self.signum = signum


def repository_root():
    return Path(__file__).resolve().parents[2]


def executable(name):
    return os.path.expanduser(os.environ.get(
        "IC_RRF_{}_BIN".format(name.upper()), str(Path.home() / ".local/bin" / name)
    ))


def exit_code(returncode):
    return returncode if returncode >= 0 else 128 - returncode


def run(command, repo, capture=False):
    """Keep native stdio; forward cancellation and reap the exact child."""
    child = subprocess.Popen(
        command, cwd=str(repo), stdout=subprocess.PIPE if capture else None,
        text=capture,
    )
    previous = {}

    def interrupt(signum, _frame):
        raise Interrupted(signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, interrupt)
        output, _ = child.communicate()
        return exit_code(child.returncode), output
    except Interrupted as error:
        # The terminal may have already signalled the child; an exited child
        # is harmless. Avoid leaving the provider alive after helper cancellation.
        for signum in previous:
            signal.signal(signum, signal.SIG_IGN)
        if child.poll() is None:
            try:
                child.send_signal(error.signum)
            except ProcessLookupError:
                pass
        try:
            child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
        return 128 + error.signum, None
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def has_option(arguments, option, abbreviations=False):
    # A literal option name after -- is a positional argument, not an override.
    for argument in arguments:
        if argument == "--":
            break
        if argument == option or argument.startswith(option + "="):
            return True
        name = argument.split("=", 1)[0]
        if abbreviations and name.startswith("--") and len(name) > 2 and option.startswith(name):
            return True
    return False


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    repo = repository_root()
    relay = [executable("relay"), "--repo", str(repo)]
    try:
        if not arguments or arguments[0] not in ("claude", "claude-plan"):
            if has_option(arguments, "--repo", abbreviations=True):
                raise ValueError("this helper fixes --repo to its own project")
            return run(relay + arguments, repo)[0]

        mode, native_arguments = arguments[0], arguments[1:]
        if mode == "claude-plan" and native_arguments:
            raise ValueError("claude-plan takes no arguments")
        if has_option(native_arguments, "--settings"):
            raise ValueError("Claude --settings conflicts with generated Relay settings")

        code, output = run(
            relay + ["--json", "provider-config", "--client", "claude"],
            repo, capture=True,
        )
        if code:
            return code
        plan = json.loads(output)
        hooks = plan.get("native_arguments") if isinstance(plan, dict) else None
        if (not isinstance(plan, dict) or plan.get("schema") != 1
                or plan.get("provider") != "claude" or plan.get("repo") != str(repo)
                or not isinstance(hooks, list) or not hooks
                or not all(isinstance(value, str) and "\0" not in value for value in hooks)):
            raise ValueError("Relay returned an invalid Claude configuration plan")
        if mode == "claude-plan":
            print(json.dumps(plan, indent=2, ensure_ascii=False))
            return 0
        return run([executable("claude")] + hooks + native_arguments, repo)[0]
    except (OSError, ValueError) as error:
        print("relay helper: {}".format(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
