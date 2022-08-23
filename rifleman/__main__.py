import os
import sys
import json

from pathlib import Path
from optparse import OptionParser

from typing import Optional, List

from . import RifleMan, Actions, Files, IGNORE


DESCRIPTION: str = """Pass '-' to read filenames from STDIN, separated by newlines"""

CONF_RAW: str = (
    "https://raw.githubusercontent.com/seanbreckenridge/rifleman/master/config/{}"
)
FORMAT_FNAME: str = "format.conf"
LINT_FNAME: str = "lint.conf"


def _download_configuration(url: str, to_file: Path) -> None:
    import requests

    try:
        with to_file.open("wb") as out_file:
            out_file.write(requests.get(url).content)
    except Exception as e:
        print(str(e))
        print(
            "Error: Could not download '{}' to '{}'...".format(url, str(to_file)),
            file=sys.stderr,
        )
        print(
            "Download the file from that the URL and put it at {}".format(str(to_file))
        )
        raise SystemExit(1)


def find_conf_dir() -> Path:
    """Find configuration file path"""
    conf_dir: Path = Path("~/.config/rifleman").expanduser().absolute()
    if "XDG_CONFIG_HOME" in os.environ and os.environ["XDG_CONFIG_HOME"]:
        conf_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "rifleman"
    if not conf_dir.exists():
        print("Creating configuration directory...")
        conf_dir.mkdir(exist_ok=True)
        default_format_conf: Path = conf_dir / FORMAT_FNAME
        default_lint_conf: Path = conf_dir / LINT_FNAME
        if not default_format_conf.exists():
            print("Downloading format.conf...")
            _download_configuration(CONF_RAW.format(FORMAT_FNAME), default_format_conf)
        if not default_lint_conf.exists():
            print("Downloading lint.conf...")
            _download_configuration(CONF_RAW.format(LINT_FNAME), default_lint_conf)
    return conf_dir


def main() -> None:
    """Handles parsing arguments from the user"""

    conf_dir: Path = find_conf_dir()
    conf_files: List[str] = [p.stem for p in Path(conf_dir).glob("*.conf")]

    parser = OptionParser(
        usage="rifleman [-] [-ljpcah] [files]...", description=DESCRIPTION
    )
    parser.add_option(
        "-l",
        action="store_true",
        help="list actions for files",
    )
    parser.add_option(
        "-j",
        action="store_true",
        help="list actions for files as JSON",
    )
    parser.add_option(
        "-m",
        action="store_true",
        help="list computed mime type for each file",
    )
    parser.add_option(
        "-p",
        action="store_true",
        help="prompt before running each command",
    )
    parser.add_option(
        "-c",
        type="string",
        default=str(conf_dir / "format.conf"),
        metavar="CONFIG_FILE",
        help="read config from specified file instead of default",
    )
    parser.add_option(
        "-a",
        type="string",
        default=None,
        metavar="ACTION",
        help="name of configuration file in config directory to use ({})".format(
            "|".join(conf_files)
        ),
    )
    options, positionals = parser.parse_args()
    if positionals == ["-"]:
        # replace positional arguments with lines from STDIN
        positionals = []
        for ln in sys.stdin.readlines():
            lns: str = ln.rstrip(os.linesep)
            if lns:
                positionals.append(lns)
    if not positionals:
        parser.print_help()
        raise SystemExit(1)

    conf_path: Path = Path(options.c)
    if options.a is not None:
        conf_slug: str = options.a
        # try to create a path which correspondings to this action
        act_path: Path = conf_dir / f"{conf_slug}.conf"
        if not act_path.exists():
            print(
                f"Specified configuration file not found: {str(act_path)}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        conf_path = act_path
    if not conf_path.exists():
        print(
            f"Specified configuration file not found: {str(conf_path)}", file=sys.stderr
        )
        raise SystemExit(1)
    if not conf_path.is_file():
        print(
            f"Specified configuration file is not a file: {options.c}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    rfman = RifleMan(conf_path)
    rfman.reload_config()
    resp: Optional[str] = run(
        rfman, options.l, options.j, options.m, options.p, positionals
    )
    if resp is not None:
        print(resp)


def confirm(message: str) -> bool:
    """
    Prompt the user to run a command
    """
    p_msg = f"Command: {message}\nRun? [Y/n] "
    while True:
        try:
            resp: str = input(p_msg).strip()
            return resp not in ["no", "n", "0", "off", "false", "f"]
        except EOFError:
            return False


def run(
    rfman: RifleMan,
    list_actions: bool,
    json_actions: bool,
    print_mimetypes: bool,
    prompt_before_executing: bool,
    files: Files,
) -> Optional[str]:
    # main wrapper
    # if user provided a flag to print actions
    # as a list or as JSON, returns the stirng to print

    if print_mimetypes:
        mbuf: str = ""
        for file in files:
            mbuf += "{}:{}\n".format(file, rfman.get_mimetype(file))
        return mbuf.strip()

    actions: Actions = rfman.collect_actions(files)

    if json_actions:
        return json.dumps(actions, indent=4, sort_keys=True)
    elif list_actions:
        buf: str = ""
        for action, files in actions.items():
            buf += "{}:\n{}".format(action, "\n".join("\t" + f for f in files) + "\n")
        return buf.strip()
    else:
        for action, files in actions.items():
            if action == IGNORE:
                print(
                    "No action for files: {}".format(
                        ", ".join([f"'{fl}'" for fl in files])
                    ),
                    file=sys.stderr,
                )
            else:
                rfman.execute(
                    action,
                    files,
                    prompt_func=confirm if prompt_before_executing else None,
                )
    return None


if __name__ == "__main__":
    main()
