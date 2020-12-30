# rifleman

[![PyPi version](https://img.shields.io/pypi/v/rifleman.svg)](https://pypi.python.org/pypi/rifleman) [![Python 3.6|3.7|3.8|3.9](https://img.shields.io/pypi/pyversions/rifleman.svg)](https://pypi.python.org/pypi/rifleman) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

An extendible dispatcher to lint/format code, based on [rifle](https://github.com/ranger/ranger)

This lets you run one command over lots of files/directories which could be in different languages - it classifies them by inspecting the mime type, extension, name or shebang, and then runs a command on those files.

This heavily simplifies and modifies the rifle config file format; including a condition to help check the 'shebang' value for scripts.

See [config/format.conf](./config/format.conf) for the default configuration file, I recommend you customize it to include the commands you use.

By default, I've included lots of the `format`ers/`lint`ers I use, an excerpt:

```yaml
# html
ext x?html?, has prettier = prettier -w "$@"
# web technologies, handled by prettier
ext vue|yaml|json|graphql|tsx?|jsx?|s?css|less|md, has prettier = prettier -w "$@"

# golang
ext go, has go = go fmt "$@"

# python
ext py, has black = black "$@"
mime text/x-script.python, has black = black "$@"
shebang python(2|3)?, has black = black "$@"

# shell script
shebang zsh|bash, has shfmt = shfmt -w "$@"
shebang \/bin\/sh, has shfmt = shfmt -w "$@"
ext sh|(ba|z)sh, has shfmt = shfmt -w "$@"
mime text/x-shellscript, has shfmt = shfmt -w "$@"
```

Used [emacs-format-all-the-code](https://github.com/lassik/emacs-format-all-the-code) as reference.

Though the example is here is for code, similar to rifle, this could be used to dispatch against any file/mime type. I've included [image.conf](config/image.conf), which takes any files as inputs, matches the `image/png|jpeg|gif` mimetypes, and runs `optipng`/`jpegtran`/`gifsicle` to optimize those files to reduce their file size. That could be run like `fd -X rifleman -a image`, to optimize all images in any subdirectores.

Feel free to PR additional formatters!

## Installation

Requires `python3.6+`

To install with pip, run:

    pip install rifleman

---

## Usage

```
Usage: rifleman [-] [-ljpcah] [files]...

Pass '-' to read filenames from STDIN, separated by newlines

Options:
  -h, --help      show this help message and exit
  -l              list actions for files
  -j              list actions for files as JSON
  -m              list computed mime type for each file
  -p              prompt before running each command
  -c CONFIG_FILE  read config from specified file instead of default
  -a ACTION       name of configuration file in config directory to use
                  (lint|format|image)
```

This doesn't offer a way to discover/search for files, because so many tools already exist to do that.

With shell globbing:

```bash
rifleman *.md ./project/*.py
```

To run this against all files in a git-tracked directory:

```bash
git ls-files | rifleman -
```

You can `find` (with the `-exec` flag), or the friendlier [`fd`](https://github.com/sharkdp/fd), to run against all files in the directory recursively:

```bash
fd -X rifleman
```

The `-j` and `-l` flags print what commands which would be used on each file instead of running the command.

The `-c` and `-a` files are used to determine which config file to use, completely altering the functionality of this.

By default, it uses the `format.conf` file in the `${XDG_CONFIG_HOME:-${HOME}/.config}/rifleman` directory. `-a` is a shorthand; specifying `-a lint` looks for a file in the configuration directory called `lint.conf`

When this is first run, it will try to download the configuration files into the corresponding directories.

If you're trying to debug which mimetype to use for a particular file, you can use the `-m` flag, to dump the mimetype `rifleman` determines.

```bash
$ git ls-files | shuf -n 3 | rifleman - -m
pytest.ini:text/plain
rifleman/py.typed:inode/x-empty
rifleman/__main__.py:text/x-python
```

For reference, that works by checking the known user-defined mimetypes at `~/.mime.types`, using the builtin [`mimetypes`](https://docs.python.org/3/library/mimetypes.html) python module. If that fails to find a mimetype, it runs the command: `file --mime-type -Lb <file>`.

### Example

```bash
$ rifleman *.md $(fd \.py$)
Running: /bin/sh -c set -- 'README.md'; prettier -w "$@"
README.md 88ms
Running: /bin/sh -c set -- 'rifleman/__init__.py' 'rifleman/__main__.py' 'setup.py' 'tests/test_rifleman.py'; black "$@"
All done! ✨ 🍰 ✨
4 files left unchanged.
```

### Tests

```bash
git clone 'https://github.com/seanbreckenridge/rifleman'
cd ./rifleman
pip install '.[testing]'
mypy ./rifleman
pytest
```
