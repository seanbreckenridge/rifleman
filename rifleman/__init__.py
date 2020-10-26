import os
import sys
import re

from pathlib import Path
from subprocess import Popen, PIPE
from collections import defaultdict

from typing import Optional, List, Union, Dict, Tuple, Mapping, Set, Callable

# Options and constants that a user might want to change:

DEFAULT_PAGER = "less"
DEFAULT_EDITOR = "vim"
ENCODING = "utf-8"
# number of lines to check before skipping this file
SHEBANG_LIMIT = 50

IGNORE = "ignore"
_CACHED_EXECUTABLES: Set[str] = set()

PathIsh = Union[str, Path]
Cmd = str
Condition = Union[Tuple[str, str], Tuple[str, ...]]
Files = List[str]
Actions = Mapping[str, Files]


def _normalize(p: PathIsh) -> Path:
    if isinstance(p, str):
        return Path(p)
    else:
        return p


def get_executables() -> Set[str]:
    """Return all executable files in $PATH + Cache them."""
    global _CACHED_EXECUTABLES
    if bool(_CACHED_EXECUTABLES):
        return _CACHED_EXECUTABLES

    if "PATH" in os.environ:
        paths = os.environ["PATH"].split(":")
    else:
        paths = ["/usr/bin", "/bin"]

    from stat import S_IXOTH, S_IFREG

    paths_seen = set()
    _CACHED_EXECUTABLES = set()
    for path in paths:
        if path in paths_seen:
            continue
        paths_seen.add(path)
        try:
            content = os.listdir(path)
        except OSError:
            continue
        for item in content:
            abspath = path + "/" + item
            try:
                filestat = os.stat(abspath)
            except OSError:
                continue
            if filestat.st_mode & (S_IXOTH | S_IFREG):
                _CACHED_EXECUTABLES.add(item)
    return _CACHED_EXECUTABLES


def extract_shebang(fname: str) -> Optional[str]:
    i: int = 0
    try:
        with open(fname, "r") as f:
            for ln in f:
                line = ln.strip()
                if line.startswith("#!"):
                    return line
                i += 1
                if i > SHEBANG_LIMIT:
                    break
    except UnicodeDecodeError:
        pass
    return None


def _is_terminal() -> bool:
    # Check if stdin (file descriptor 0), stdout (fd 1) and
    # stderr (fd 2) are connected to a terminal
    try:
        os.ttyname(0)
        os.ttyname(1)
        os.ttyname(2)
    except OSError:
        return False
    return True


def Popen_handler(
    cmd: List[str],
    print_cmd: bool = True,
    prompt_func: Optional[Callable[[str], bool]] = None,
) -> None:
    cmd_str: str = " ".join(cmd)
    if prompt_func is not None:
        if not prompt_func(cmd_str):
            return
    if print_cmd:
        print("Running: {}".format(cmd_str))
    Popen(cmd).wait()


class RifleMan:
    delimiter1 = "="
    delimiter2 = ","

    @staticmethod
    def logger(string: str) -> None:
        sys.stderr.write(string + "\n")

    def __init__(self, config_file: PathIsh):
        self.config_file: Path = _normalize(config_file)
        self._initialized_mimetypes: bool = False
        # maps filenames to mimetypes
        self._mimetypes: Dict[str, str] = {}
        self.rules: List[Tuple[Cmd, Condition]] = []

        # get paths for mimetype files
        self._mimetype_known_files: List[str] = [os.path.expanduser("~/.mime.types")]
        self._prefix: List[str] = ["/bin/sh", "-c"]

        if "PAGER" not in os.environ:
            os.environ["PAGER"] = DEFAULT_PAGER
        if "EDITOR" not in os.environ:
            os.environ["EDITOR"] = os.environ.get("VISUAL", DEFAULT_EDITOR)

    def reload_config(self, config_file: Optional[PathIsh] = None) -> None:
        """Replace the current configuration with the one in config_file"""
        if config_file is None:
            config_file = self.config_file
        fobj = _normalize(config_file).open("r")
        self.rules = []
        for line in fobj:
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            if self.delimiter1 not in line:
                raise ValueError("Line without delimiter")
            tests, command = line.split(self.delimiter1, 1)
            test_conditions = tests.split(self.delimiter2)
            test_tup: Condition = tuple(tuple(f.strip().split(None, 1)) for f in test_conditions)  # type: ignore[misc]
            self.rules.append((command.strip(), test_tup))
        fobj.close()

    def _eval_condition(self, condition: Condition, fname: str) -> bool:
        # Handle the negation of conditions starting with an exclamation mark,
        # then pass on the arguments to _eval_condition2().

        if not condition:
            return True
        if condition[0].startswith("!"):
            new_condition = tuple([condition[0][1:]]) + tuple(condition[1:])
            return not self._eval_condition2(new_condition, fname)
        return self._eval_condition2(condition, fname)

    def _eval_condition2(self, rule: Condition, fname: str) -> bool:
        # This function evaluates the condition, after _eval_condition() handled
        # negation of conditions starting with a "!".

        function: str = rule[0]
        argument: str = rule[1] if len(rule) > 1 else ""

        if function == "ext":
            if os.path.isfile(fname):
                partitions = os.path.basename(fname).rpartition(".")
                if not partitions[0]:
                    return False
                return bool(re.search("^(" + argument + ")$", partitions[2].lower()))
        elif function == "name":
            return bool(re.search(argument, os.path.basename(fname)))
        elif function == "match":
            return bool(re.search(argument, fname))
        elif function == "path":
            return bool(re.search(argument, os.path.abspath(fname)))
        elif function == "mime":
            return bool(re.search(argument, self.get_mimetype(fname)))
        elif function == "has":
            if argument.startswith("$"):
                if argument[1:] in os.environ:
                    return os.environ[argument[1:]] in get_executables()
                return False
            else:
                return argument in get_executables()
        elif function == "shebang":
            shebang = extract_shebang(fname)
            if shebang is not None:
                return bool(re.search(argument, shebang))
            return False
        elif function == "terminal":
            return _is_terminal()
        elif function == "env":
            return bool(os.environ.get(argument))
        elif function == "else":
            return True
        return False

    def get_mimetype(self, fname: str) -> str:
        # Spawn "file" to determine the mime-type of the given file.
        # add this to the dictionary of fname -> mimetype
        if fname in self._mimetypes:
            return self._mimetypes[fname]

        import mimetypes

        for path in self._mimetype_known_files:
            if path not in mimetypes.knownfiles:
                mimetypes.knownfiles.append(path)
        guessed_type, _ = mimetypes.guess_type(fname)

        if guessed_type is None:
            process = Popen(
                ["file", "--mime-type", "-Lb", fname], stdout=PIPE, stderr=PIPE
            )
            mimetype, _ = process.communicate()
            guessed_type = mimetype.decode(ENCODING).strip()
            if guessed_type == "application/octet-stream":
                try:
                    process = Popen(
                        ["mimetype", "--output-format", "%m", fname],
                        stdout=PIPE,
                        stderr=PIPE,
                    )
                    mimetype, _ = process.communicate()
                    guessed_type = mimetype.decode(ENCODING).strip()
                except OSError:
                    pass
        self._mimetypes[fname] = guessed_type
        return guessed_type

    def collect_actions(self, files: Files) -> Actions:
        actions: Actions = defaultdict(list)
        for fname in files:
            if not os.path.exists(fname):
                self.__class__.logger("Path doesn't exist: {}".format(fname))
            if not os.path.isfile(fname):  # ignore non-files
                continue
            for cmd, tests in self.rules:
                for test in tests:
                    # unsure why mypy cant catch that test is of type Condition
                    if not self._eval_condition(test, fname):  # type: ignore[arg-type]
                        break  # break out of tests
                else:
                    # none of the rules failed, this matches the action
                    actions[cmd].append(fname)
                    break  # break out of rules
            else:
                # if no rules matched - this didnt match any conditions
                actions[IGNORE].append(fname)
        return actions

    def _build_command(self, files: Files, action: str) -> str:
        """
        Creates the command string for each action
        """
        filenames = "' '".join(
            f.replace("'", "'\\''") for f in files if "\x00" not in f
        )
        return "set -- '%s'; %s" % (filenames, action)

    def execute(
        self,
        action: str,
        files: Files,
        prompt_func: Optional[Callable[[str], bool]] = None,
    ) -> None:
        """
        Executes the action for the given files
        """
        # probably not needed here as checked in __main__
        # leaving for possible library-usage
        if action != IGNORE:
            # if '$1' is specified, run action once for each file
            if '"$1"' in action:
                for fname in files:
                    Popen_handler(
                        self._prefix + [self._build_command([fname], action)],
                        prompt_func=prompt_func,
                    )
            else:
                Popen_handler(
                    self._prefix + [self._build_command(files, action)],
                    prompt_func=prompt_func,
                )
