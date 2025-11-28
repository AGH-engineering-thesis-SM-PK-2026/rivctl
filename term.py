import curses
import signal
import pathlib
import sys


_color_inits = []


def def_color(fg, bg):
    key = len(_color_inits) + 1

    def init():
        curses.init_pair(key, fg, bg)

    def use():
        return curses.color_pair(key)

    _color_inits.append(init)
    return use


def color_init():
    for init_fn in _color_inits:
        init_fn()


# colors!
whcy = def_color(curses.COLOR_WHITE, curses.COLOR_CYAN)
whbl = def_color(curses.COLOR_WHITE, curses.COLOR_BLUE)
whbk = def_color(curses.COLOR_WHITE, curses.COLOR_BLACK)
yebl = def_color(curses.COLOR_YELLOW, curses.COLOR_BLUE)
yebk = def_color(curses.COLOR_YELLOW, curses.COLOR_BLACK)
cywh = def_color(curses.COLOR_CYAN, curses.COLOR_WHITE)
cybk = def_color(curses.COLOR_CYAN, curses.COLOR_BLACK)
blwh = def_color(curses.COLOR_BLUE, curses.COLOR_WHITE)
blcy = def_color(curses.COLOR_BLUE, curses.COLOR_CYAN)
grbk = def_color(curses.COLOR_GREEN, curses.COLOR_BLACK)
mabk = def_color(curses.COLOR_MAGENTA, curses.COLOR_BLACK)
bkwh = def_color(curses.COLOR_BLACK, curses.COLOR_WHITE)
bkcy = def_color(curses.COLOR_BLACK, curses.COLOR_CYAN)
bkgr = def_color(curses.COLOR_BLACK, curses.COLOR_GREEN)
bkbk = def_color(curses.COLOR_BLACK, curses.COLOR_BLACK)

# horizontal window padding/button spacing
_hp = 2


class WindowError(Exception):
    pass


def _bg(win, color):
    win.clear()
    win.bkgd(' ', color)


def _txt(win, text, pos, color):
    x, y = pos
    win.addstr(y, x, text, color)


def _box(win, char, pos, size, color):
    x, y = pos
    w, h = size
    win.attron(color)
    for v in range(y, y + h):
        win.hline(v, x, char, w)
    win.attroff(color)


def _window(title, sz, pos=(0, 0), keypad=False, fg=bkwh):
    w, h = sz
    x, y = pos
    try:
        win = curses.newwin(h, w, y, x)
        win.attron(fg())
        win.box()
        win.attroff(fg())
        win.keypad(keypad)
        win.bkgd(' ', fg())
        if title:
            _txt(win, f' {title} ', (_hp, 0), fg())
        return win
    except CursesError:
        raise WindowError('invalid window pos/size')


def _window_sz(win):
    y, x = win.getmaxyx()
    return x, y


def close_window(win):
    win.erase()
    del win


def _draw_btns(win, btns, y, sel):
    labels = [f'  {label}  ' for label, _ in btns]

    w, _ = _window_sz(win)
    wbtn = sum([len(label) + _hp for label in labels])
    x = w - wbtn
    for i, label in enumerate(labels):
        color = cybk() if sel == i else cywh()
        _txt(win, label, (x, y), color)
        x += len(label) + _hp


def _draw_input(win, text, y, focus):
    w, _ = _window_sz(win)
    wi = w - _hp*2
    cut = text[-wi+1:]

    color = cybk() if focus else whbk()
    pos = (_hp, y)
    _box(win, ' ', pos, (wi, 1), color)
    _txt(win, cut, pos, color)
    if focus:
        _txt(win, '█', (len(cut) + _hp, y), color)


def _draw_outline(win, pos, sz, color, title=None, label=None):
    x, y = pos
    w, h = sz
    top = '┌' + '─' * w + '┐'
    bottom = '└' + '─' * w + '┘'
    _txt(win, top, (x - 1, y - 1), color)
    _txt(win, bottom, (x - 1, y + h), color)
    for v in range(y, y + h):
        _txt(win, '│', (x - 1, v), color)
        _txt(win, '│', (x + w, v), color)
    if title:
        title_text, title_color = title
        _txt(win, f' {title_text} ', (x, y - 1), title_color or color)
    if label:
        label_text, label_color = label
        u = x + w - len(label_text) - 4
        _txt(win, f' {label_text} ', (u, y + h), label_color or color)


def _draw_scroll_bar(win, pos, h, r, pct, color):
    x, y = pos
    t = int(pct * 0.99 * (h - r * 2)) + r
    for v in range(h):
        track = v >= t - r and v <= t + r
        _txt(win, '█' if track else '│', (x, v + y), color)


def _toast(title, message, hx=0):
    lines = message.split('\n')

    w = max([len(line) for line in lines]) + _hp*2
    h = len(lines) + 5 + hx
    win = _window(title, (w, h), (2, 2), keypad=True)
    for i, line in enumerate(lines):
        _txt(win, line, (_hp, i + 2), bkwh())

    return win


def popup(title, message, btns):
    win = _toast(title, message)
    _, h = _window_sz(win)

    accept_ev = False
    btn_sel = len(btns) - 1

    def redraw():
        _draw_btns(win, btns, h - 2, btn_sel)
        win.refresh()

    def update(poll):
        nonlocal accept_ev, btn_sel
        ev, arg = poll
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            mx, _ = arg
            btn_sel = max(min(btn_sel + mx, len(btns) - 1), 0)
        elif ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc':
                return 'quit'
            elif arg == 'enter':
                _, action = btns[btn_sel]
                if action:
                    return action(None)
                return 'quit'
        return 'ok'

    def close():
        win.erase()
    
    return redraw, update, close


def dialog(title, message, btns):
    win = _toast(title, message, 1)
    _, h = _window_sz(win)

    accept_ev = False
    input_sel = True
    btn_sel = len(btns) - 1
    text = ''

    def redraw():
        _draw_input(win, text, h - 4, input_sel)
        _draw_btns(win, btns, h - 2, btn_sel if not input_sel else -1)
        win.refresh()

    def update(poll):
        nonlocal accept_ev, input_sel, btn_sel, text
        ev, arg = poll
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            mx, my = arg
            if my == -1:
                input_sel = False
            elif my == +1:
                input_sel = True
            if not input_sel:
                btn_sel = max(min(btn_sel + mx, len(btns) - 1), 0)
        elif ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc':
                return 'quit'
            elif arg == 'enter' and input_sel:
                input_sel = False
            elif arg == 'enter':
                _, action = btns[btn_sel]
                if action:
                    return action(text)
                return 'quit'
            elif arg == 'del' and input_sel:
                text = text[:-1]
            elif input_sel:
                text += arg
        return 'ok'

    def close():
        win.erase()

    return redraw, update, close


def pager(title, text, sz, btns, fg=bkwh):
    vw, vh = sz
    lines = text.split('\n')
    bottom = len(lines) - vh

    # empty message, will be drawn later
    win = _window(title, (vw + 3, vh + 5), (2, 2), keypad=True)
    w, h = _window_sz(win)

    accept_ev = False
    row = 0
    btn_sel = len(btns) - 1

    def redraw():
        for i in range(row, row+vh):
            y = i - row + 2
            _box(win, ' ', (_hp, y), (vw - 1, 1), fg())
            try:
                _txt(win, lines[i][:vw - 6], (_hp, y), fg())
            except IndexError:
                pass
        if bottom > 0:
            _draw_scroll_bar(win, (w - 3, 2), vh, 1, row / bottom, fg())
        _draw_btns(win, btns, h - 2, btn_sel)
        win.refresh()

    def update(poll):
        nonlocal accept_ev, row, btn_sel
        ev, arg = poll
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            mx, my = arg
            row = max(min(row - my, bottom), 0)
            btn_sel = max(min(btn_sel + mx, len(btns) - 1), 0)
        elif ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc':
                return 'quit'
            elif arg == 'enter':
                _, action = btns[btn_sel]
                if action:
                    return action(None)
                return 'quit'
        return 'ok'

    def close():
        win.erase()    

    return redraw, update, close


def menu(pos, acts):
    w = max([len(text) for text, _ in acts]) + 2
    h = len(acts) + 2

    win = _window(None, (w, h), pos, fg=whcy)

    accept_ev = False
    act_sel = 0

    def _draw_acts(y, sel):
        for i, (text, _) in enumerate(acts):
            if text == '-':
                
                line = '─' * (w - 2)
                _txt(win, f'├{line}┤', (0, y + i), whcy())
            else:
                color = cybk() if i == sel else whcy()
                _txt(win, text, (1, y + i), color)

    def _is_sel_hline(sel):
        text, _ = acts[sel]
        return text == '-'

    def redraw():
        _draw_acts(1, act_sel)
        win.refresh()

    def update(poll):
        nonlocal accept_ev, act_sel
        ev, arg = poll
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            _, my = arg
            act_sel = max(min(act_sel - my, len(acts) - 1), 0)
            if _is_sel_hline(act_sel):
                act_sel = max(min(act_sel - my, len(acts) - 1), 0)
        elif ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc':
                return 'quit'
            elif arg == 'enter':
                _, action = acts[act_sel]
                if action:
                    return action(None)
                return 'quit'
        return 'ok'

    def close():
        win.erase()
    
    return redraw, update, close


def picker(title, sz, act, fc=whbk, dc=cybk, sc=bkcy, init='.'):
    vw, vh = sz

    # empty message, will be drawn later
    win = _window(title, (vw + 3, vh + 5), (2, 2), keypad=True)
    w, h = _window_sz(win)

    accept_ev = False
    row = 0
    sel = 0

    path = pathlib.Path(init)
    items = []

    def redraw():
        bottom = len(items) - vh
        for i in range(row, row+vh):
            y = i - row + 2
            _box(win, ' ', (_hp, y), (vw - 1, 1), fc())
            try:
                item = items[i]
                name = f'-{item.name}/' if item.is_dir() else f'-{item.name}'
                if i == sel:
                    _txt(win, name[:vw-6], (_hp, y), sc())
                else:
                    color = dc() if item.is_dir() else fc()
                    _txt(win, name[:vw-6], (_hp, y), color)
            except IndexError:
                pass
        if bottom > 0:
            _draw_scroll_bar(win, (w - 3, 2), vh, 1, row / bottom, fc())
        win.refresh()

    def _path_to_items(p):
        parent = p.joinpath(pathlib.Path('..'))
        items = list(p.glob('*'))
        dirs = filter(lambda item: item.is_dir(), items)
        files = filter(lambda item: not item.is_dir(), items)
        return [parent] + list(dirs) + list(files)

    def update(poll):
        nonlocal path, items, accept_ev, row, sel
        ev, arg = poll
        items = _path_to_items(path)
        bottom = len(items) - vh
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            _, my = arg
            max_sel = len(items) - 1
            cnt = vh // 2
            sel = max(min(sel - my, max_sel), 0)
            row = max(min(sel - cnt, bottom), 0)
        elif ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc':
                return 'quit'
            elif arg == 'enter':
                item = items[sel]
                if item.is_dir():
                    path = item
                    return 'ok'
                return act(item)
        return 'ok'

    def close():
        win.erase()    

    return redraw, update, close


def abort(win, title, message):
    _bg(win, whbl())

    try:
        redraw, update, _ = popup(title, message, [('exit', None)])
        while update(poll_user(win)) != 'quit':
            redraw()
    except WindowError:
        print(f'exit: {title}')
        for line in message.split('\n'):
            print(f'  {line}')
    sys.exit(1)


def ensure_vga(win):
    w, h = _window_sz(win)
    if h < 24 or w < 80:
        abort(win, 'Bad Size', 'Terminal size must be at least 80x24')


_regs_names = [
    'zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2',
    's0', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
    'a6', 'a7', 's2', 's3', 's4', 's5', 's5', 's7',
    's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6'
]


def main_view(win, page, tab):
    _bg(win, whbl())

    rx = 2
    mx = 38
    oy = 4

    if page:
        regs_vals = ['00000000'] + page.regs.split(',')[:31]
        _txt(win, 'pc    ', (rx + 1, oy), yebl())
        _txt(win, f'{page.pc:8}', (rx + 7, oy), whbl())
        for i, reg_name, reg_val in zip(range(32), _regs_names, regs_vals):
            x = (0 if i < 16 else 16) + rx + 1
            y = i % 16 + oy + 2
            _txt(win, f'{reg_name:6}', (x, y), yebl())
            _txt(win, f'{reg_val:8}', (x + 6, y), whbl())
    else:
        _txt(win, 'no pages yet', (rx + 2, 6), whbl())

    if page:
        data_vals = ['00000000'] * 32
        for i, data_val in zip(range(32), data_vals):
            x = i % 4 * 10 + mx + 1
            y = i // 4 + oy
            _txt(win, f'{data_val:8}', (x, y), whbl())
    else:
        _txt(win, 'no pages yet', (mx + 2, 6), whbl())

    if page:
        prog_vals = [
            ('00000044', 'addi x11, x0, 20'),
            ('00000048', 'lui x11 1'),
            ('0000004c', 'addi x11, x11, 4'),
            ('00000050', 'sw x11, 0(x12)')
        ] + [None] * 5
        for i, prog_val in zip(range(8), prog_vals):
            y = i + oy + 10
            if prog_val:
                paddr, instr = prog_val
                mnemo, params = instr.split(' ', 1)
                _txt(win, f'{paddr:8}', (mx + 1, y), yebl())
                _txt(win, f'{mnemo:6}{params}', (mx + 11, y), whbl())
            else:
                _txt(win, '--------', (mx + 1, y), yebl())
                _txt(win, '-', (mx + 11, y), whbl())
    else:
        _txt(win, 'no pages yet', (mx + 2, 16), whbl())
        
    _draw_outline(
        win, 
        (rx, 4), (32, 18), whbl(), 
        ('regfile', blwh() if tab == 0 else None)
    )
    _draw_outline(
        win, 
        (mx, 4), (40, 8), whbl(),
        ('datamem', blwh() if tab == 1 else None), 
        ('offset: 00000000' if page else 'offset:      N/A', None) 
    )
    _draw_outline(
        win, 
        (mx, 14), (40, 8), whbl(), 
        ('progmem', blwh() if tab == 2 else None),
        ('offset: 00000044' if page else 'offset:      N/A', None)
    )


def task_bar(win, uart_model):
    w, h = _window_sz(win)
    y = h - 1

    _box(win, ' ', (0, y), (w, 1), whbk())

    if uart_model.dev:
        short_dev = uart_model.dev.split('/')[-1]
        ox = len(short_dev)
        wo = w - ox
        _txt(win, '■', (wo - 11, y), bkbk() if uart_model.rxc & 1 else grbk())
        _txt(win, '■', (wo - 10, y), bkbk() if uart_model.txc & 1 else yebk())
        _txt(win, f' <-> {short_dev}', (wo - 9, y), whbk())
    else:
        msg = ' <-> <nil>'
        ox = len(msg)
        wo = w - ox
        _txt(win, f' {msg} ', (wo - 9, y), whbk())
        
    _txt(win, ' h ', (0, y), whbk())
    _txt(win, 'Halt   ', (3, y), bkcy())  
    _txt(win, ' z ', (10, y), whbk())
    _txt(win, 'Run    ', (13, y), bkcy())
    _txt(win, ' a ', (20, y), whbk())
    _txt(win, 'Cycle  ', (23, y), bkcy())
    _txt(win, ' s ', (30, y), whbk())
    _txt(win, 'Step   ', (33, y), bkcy())
    _txt(win, ' r ', (40, y), whbk())
    _txt(win, 'Reset  ', (43, y), bkcy())


_ctl_mode_colors = {
    'ready*': yebk,
    'halted': mabk,
    'reset*': yebk,
    '<step>': cybk,
    '<*   >': grbk,
    '< *  >': grbk,
    '<  * >': grbk,
    '<   *>': grbk,
}


def top_bar(win, mode_model, page_model, acts):
    w, _ = _window_sz(win)
    _box(win, ' ', (0, 0), (w, 1), bkcy())
    page_desc = f'page {page_model.now:4}/{page_model.top:4}'
    ox = len(page_desc)
    _txt(win, page_desc, (w - ox - 10, 0), bkcy())

    color = _ctl_mode_colors.get(mode_model.ctl, cybk)()
    _txt(win, f' {mode_model.ctl} ', (w - 8, 0), color)

    def _draw_btn(text, x):
        _txt(win, text, (x + 1, 0), bkcy())
        return x + len(text) + 2

    x = 1
    for act in acts:
        x = _draw_btn(act, x)


def poll_user(win):
    key = win.getch()
    if key == -1:
        return 'empty', None
    if key == curses.KEY_RESIZE:
        return 'resize', None
    elif key == 27:
        return 'key', 'esc'
    elif key == 10:
        return 'key', 'enter'
    elif key == 8:
        return 'key', 'del'
    elif key == 9:
        return 'key', 'tab'
    elif key == curses.KEY_UP:
        return 'move', (0, +1)
    elif key == curses.KEY_DOWN:
        return 'move', (0, -1)
    elif key == curses.KEY_LEFT:
        return 'move', (-1, 0)
    elif key == curses.KEY_RIGHT:
        return 'move', (+1, 0)
    else:
        return 'key', chr(key)


def run(main):
    def wrapped(scr):
        curses.curs_set(0)
        color_init()
        main(scr)

    def interrupt_handler(_signum, _frame):
        print('exit: interrupted')
        exit(0)

    signal.signal(signal.SIGINT, interrupt_handler)
    curses.wrapper(wrapped)


CursesError = curses.error
