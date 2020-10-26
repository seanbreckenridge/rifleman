import os
import sys
import json

from pathlib import Path
from optparse import OptionParser

from typing import Optional

from . import RifleMan, Actions, Files


def find_conf_dir() -> Path:
    """Find configuration file path"""
    conf_dir: Path = Path("~/.config/rifleman").absolute()
    if "XDG_CONFIG_HOME" in os.environ and os.environ["XDG_CONFIG_HOME"]:
        conf_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "rifleman"
    if not conf_dir.exists():
        print("Creating configuration directory...")
        conf_dir.mkdir(exist_ok=True)
    default_format_conf: Path = conf_dir / 'format.conf'
    default_lint_conf: Path = conf_dir / 'lint.conf'
    if not default_format_conf.exists():
        print("Copying format.conf...")
    if not default_lint_conf.exists():
        print("Copying lint.conf...")
    return conf_dir


def main() -> None:
    """Handles parsing arguments from the user"""

    conf_dir: Path = find_conf_dir()

    parser = OptionParser(usage="rifleman [-ljcah] [files]...")
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
            "|".join([c.rstrip(".conf") for c in os.listdir(str(conf_dir))])
        ),
    )
    options, positionals = parser.parse_args()
    if not positionals:
        parser.print_help()
        raise SystemExit(1)

    conf_path: Path = Path(options.c)
    if options.a is not None:
        conf_slug: str = options.a.rstrip(".conf")
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
    resp: Optional[str] = run(rfman, options.l, options.j, positionals)
    if resp is not None:
        print(resp)


def run(
    rfman: RifleMan, list_actions: bool, json_actions: bool, files: Files
) -> Optional[str]:
    # main wrapper
    # if user provided a flag to print actions
    # as a list or as JSON, returns the stirng to print

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
            rfman.execute(action, files)
    return None


if __name__ == "__main__":
    main()
