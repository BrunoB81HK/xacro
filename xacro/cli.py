# Copyright (c) 2015, Open Source Robotics Foundation, Inc.
# Copyright (c) 2013, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Open Source Robotics Foundation, Inc.
#       nor the names of its contributors may be used to endorse or promote
#       products derived from this software without specific prior
#       written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Authors: Stuart Glaser, William Woodall, Robert Haschke
# Maintainer: Morgan Quigley <morgan@osrfoundation.org>

import optparse
import sys
import textwrap
import typing

__all__ = (
    "error",
    "process_args",
)


_ansi = {"red": 91, "yellow": 93}  # bold colors
REMAP = ":="  # copied from rosgraph.names


def colorize(
    msg: str, color: str, file: typing.TextIO = sys.stderr, alt_text: str = ""
) -> str:
    color = _ansi.get(color, None)

    if color and hasattr(file, "isatty") and file.isatty():
        return f"\033[{color:d}m{msg:s}\033[0m"

    return f"{alt_text:s}{msg:s}"


def message(msg: str, *args, **kwargs) -> None:
    file = kwargs.get("file", sys.stderr)
    alt_text = kwargs.get("alt_text", None)
    color = kwargs.get("color", None)
    print(colorize(msg, color, file, alt_text), *args, file=file)


def warning(*args, **kwargs) -> None:
    defaults = dict(file=sys.stderr, alt_text="warning: ", color="yellow")
    defaults.update(kwargs)
    message(*args, **defaults)


def error(*args, **kwargs) -> None:
    defaults = dict(file=sys.stderr, alt_text="error: ", color="red")
    defaults.update(kwargs)
    message(*args, **defaults)


class ColoredOptionParser(optparse.OptionParser):
    def error(self, message: str) -> None:
        msg = colorize(message, "red")
        optparse.OptionParser.error(self, msg)


class IndentedHelpFormatterWithNL(optparse.IndentedHelpFormatter):
    _original_wrap = textwrap.wrap

    def __init__(self, *args, **kwargs) -> None:
        optparse.IndentedHelpFormatter.__init__(self, *args, **kwargs)

    @classmethod
    def wrap_with_newlines(cls, text: str, width: int, **kwargs) -> list[str]:
        result = list()
        for paragraph in text.split("\n"):
            result.extend(cls._original_wrap(paragraph, width, **kwargs))
        return result

    def format_option(self, text: str) -> str:
        textwrap.wrap, old = (
            IndentedHelpFormatterWithNL.wrap_with_newlines,
            textwrap.wrap,
        )
        result = optparse.IndentedHelpFormatter.format_option(self, text)
        textwrap.wrap = old
        return result


def load_mappings(argv: str) -> dict[str, str]:
    """
    Load name mappings encoded in command-line arguments. This will filter
    out any parameter assignment mappings.

    @param argv: command-line arguments
    @type  argv: [str]
    @return: name->name remappings.
    @rtype: dict {str: str}
    """
    mappings = {}
    for arg in argv:
        if REMAP in arg:
            try:
                src, dst = [x.strip() for x in arg.split(REMAP)]
                if src and dst:
                    if len(src) > 1 and src[0] == "_" and src[1] != "_":
                        # ignore parameter assignment mappings
                        pass
                    else:
                        mappings[src] = dst
            except Exception:
                raise RuntimeError("Invalid remapping argument '%s'\n" % arg)
    return mappings


def process_args(argv: str, require_input: bool = True) -> tuple[dict, str]:
    parser = ColoredOptionParser(
        usage="usage: %prog [options] <input>", formatter=IndentedHelpFormatterWithNL()
    )
    parser.add_option(
        "-o",
        dest="output",
        metavar="FILE",
        help="write output to FILE instead of stdout",
    )
    parser.add_option(
        "--deps", action="store_true", dest="just_deps", help="print file dependencies"
    )
    parser.add_option(
        "--inorder",
        "-i",
        action="store_true",
        dest="in_order",
        help="processing in read order (default, can be omitted)",
    )

    # verbosity options
    parser.add_option(
        "-q",
        action="store_const",
        dest="verbosity",
        const=0,
        help="quiet operation, suppressing warnings",
    )
    parser.add_option("-v", action="count", dest="verbosity", help="increase verbosity")
    parser.add_option(
        "--verbosity",
        metavar="level",
        dest="verbosity",
        type="int",
        help="set verbosity level"
        "0: quiet, suppressing warnings"
        "1: default, showing warnings and error locations"
        "2: show stack trace"
        "3: log property definitions and usage on top level"
        "4: log property definitions and usage on all levels",
    )

    # process substitution args
    try:
        mappings = load_mappings(argv)
        filtered_args = [a for a in argv if REMAP not in a]  # filter-out REMAP args
    except ImportError as e:
        warning(e)
        mappings = {}
        filtered_args = argv

    parser.set_defaults(just_deps=False, verbosity=1)
    (options, pos_args) = parser.parse_args(filtered_args)
    if options.in_order:
        message(
            "xacro: in-order processing became default in ROS Melodic. You can drop the option."
        )
    options.in_order = True

    if len(pos_args) != 1:
        if require_input:
            parser.error("expected exactly one input file as argument")
        else:
            pos_args = [None]

    options.mappings = mappings
    return vars(options), pos_args[0]
