import locale
import sys


def make_unique(*objs):
    return tuple(dict.fromkeys(x for x in objs if x is not None))


CODEC_LIST = make_unique(
    # list of codecs to try, in order...
    # use getattr because some stream wrappers (ie, houdinit's hou.ShellIO)
    # may not have a .encoding attr
    getattr(sys.stdout, "encoding", None),
    getattr(sys.stderr, "encoding", None),
    getattr(sys.stdin, "encoding", None),
    getattr(sys.__stdout__, "encoding", None),
    getattr(sys.__stderr__, "encoding", None),
    getattr(sys.__stdin__, "encoding", None),
    locale.getpreferredencoding(),
    "utf8",
)


def try_decode(input_bytes):
    for codec in CODEC_LIST:
        try:
            return input_bytes.decode(codec)
        except UnicodeDecodeError:
            pass
    return input_bytes
