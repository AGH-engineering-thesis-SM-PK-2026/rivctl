import re

from view import InstrModel


_instr_pattern = re.compile(r'\s+([0-9a-f]+):\s+([0-9a-f]+)\s+(.+)')


def read_prog(filename):
    with open(filename) as fp:
        for line in fp.readlines():
            maybe_match = _instr_pattern.match(line)
            if maybe_match:
                loc, code, src = maybe_match.groups()
                yield InstrModel(loc, code, src)


def pad_prog(instrs, nop='00000013'):
    max_loc = max([int(loc, 16) for loc, _, _ in instrs])
    i = 0
    for out_loc in range(0, max_loc + 4, 4):
        loc, code, _ = instrs[i]
        if out_loc == int(loc, 16):
            i += 1
            yield code
        else:
            yield nop
