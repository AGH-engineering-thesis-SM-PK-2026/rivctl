import re

from data import Instr


_instr_pattern = re.compile(r'\s+([0-9a-f]+):\s+([0-9a-f]+)\s+(.+)')


def read_prog(filename):
    with open(filename) as fp:
        for line in fp.readlines():
            maybe_match = _instr_pattern.match(line)
            if maybe_match:
                loc, code, src = maybe_match.groups()
                yield Instr(loc, code, src)


# def pad_prog(instrs, nop='00000013'):
#     max_ndx = int(instrs[-1].loc, 16)
#     i = 0
#     for ndx in range(max_ndx + 1):
#         instr = instrs[i]
#         if ndx<<2 == int(instr.loc, 16):
#             i += 1
#             yield instr
#         else:
#             yield Instr(f'{ndx:08x}', nop, '# <padded>')
