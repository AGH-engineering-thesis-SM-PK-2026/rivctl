import curses
import signal
import sys

from view import get_page_mode


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
_fw = def_color(curses.COLOR_WHITE, curses.COLOR_BLUE)
_fi = def_color(curses.COLOR_BLUE, curses.COLOR_WHITE)
_fh = def_color(curses.COLOR_YELLOW, curses.COLOR_BLUE)
_po = def_color(curses.COLOR_BLACK, curses.COLOR_WHITE)
_bw = def_color(curses.COLOR_WHITE, curses.COLOR_BLACK)
_bh = def_color(curses.COLOR_CYAN, curses.COLOR_BLACK)
_bp = def_color(curses.COLOR_CYAN, curses.COLOR_WHITE)
_tr = def_color(curses.COLOR_GREEN, curses.COLOR_BLACK)
_tt = def_color(curses.COLOR_YELLOW, curses.COLOR_BLACK)
_tv = def_color(curses.COLOR_BLACK, curses.COLOR_BLACK)
_tb = def_color(curses.COLOR_BLACK, curses.COLOR_CYAN)
_mb = def_color(curses.COLOR_CYAN, curses.COLOR_BLACK)
_my = def_color(curses.COLOR_YELLOW, curses.COLOR_BLACK)

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


def _window(title, sz, pos=(0, 0), keypad=False):
    w, h = sz
    x, y = pos
    try:
        win = curses.newwin(h, w, x, y)
        win.keypad(keypad)
        win.bkgd(' ', _po())
        _box(win, ' ', (0, 0), (w, 1), _bw())
        _txt(win, f' {title} ', (_hp, 0), _po())
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
        color = _bh() if sel == i else _bp()
        _txt(win, label, (x, y), color)
        x += len(label) + _hp


def _draw_input(win, text, y, focus):
    w, _ = _window_sz(win)
    wi = w - _hp*2
    cut = text[-wi+1:]

    color = _bh() if focus else _bw()
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
        _txt(win, line, (_hp, i + 2), _po())

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


def pager(title, text, sz, btns):
    vw, vh = sz
    lines = text.split('\n')
    bottom = len(lines) - vh
    if bottom <= 0:
        # doesn't need scrolling to fit
        return popup(title, text, btns)

    # empty message, will be drawn later
    win = _toast(title, ' ' * vw, vh - 1)
    w, h = _window_sz(win)

    accept_ev = False
    row = 0
    btn_sel = len(btns) - 1

    def redraw():
        for i in range(row, row+vh):
            y = i - row + 2
            _box(win, ' ', (_hp, y), (vw, 1), _po())
            _txt(win, lines[i][:vw-2], (_hp, y), _po())
        _draw_scroll_bar(win, (w - 3, 2), vh, 1, row / bottom, _po())
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


def abort(win, title, message):
    _bg(win, _fw())

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
        abort(win, 'bad size', 'terminal size must be at least 80x24')


_regs_names = [
    'zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2',
    's0', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
    'a6', 'a7', 's2', 's3', 's4', 's5', 's5', 's7',
    's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6'
]


def main_view(win, page, tab):
    _bg(win, _fw())

    rx = 2
    mx = 38
    oy = 4

    if page:
        regs_vals = ['00000000'] + page.regs.split(',')[:31]
        _txt(win, 'pc    ', (rx + 1, oy), _fh())
        _txt(win, f'{page.pc:8}', (rx + 7, oy), _fw())
        for i, reg_name, reg_val in zip(range(32), _regs_names, regs_vals):
            x = (0 if i < 16 else 16) + rx + 1
            y = i % 16 + oy + 2
            _txt(win, f'{reg_name:6}', (x, y), _fh())
            _txt(win, f'{reg_val:8}', (x + 6, y), _fw())
    else:
        _txt(win, 'no pages yet', (rx + 2, 6), _fw())

    if page:
        data_vals = ['00000000'] * 32
        for i, data_val in zip(range(32), data_vals):
            x = i % 4 * 10 + mx + 1
            y = i // 4 + oy
            _txt(win, f'{data_val:8}', (x, y), _fw())
    else:
        _txt(win, 'no pages yet', (mx + 2, 6), _fw())

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
                _txt(win, f'{paddr:8}', (mx + 1, y), _fh())
                _txt(win, f'{mnemo:6}{params}', (mx + 11, y), _fw())
            else:
                _txt(win, '--------', (mx + 1, y), _fh())
                _txt(win, '-', (mx + 11, y), _fw())
    else:
        _txt(win, 'no pages yet', (mx + 2, 16), _fw())
        
    _draw_outline(
        win, 
        (rx, 4), (32, 18), _fw(), 
        ('regfile', _fi() if tab == 0 else None)
    )
    _draw_outline(
        win, 
        (mx, 4), (40, 8), _fw(),
        ('datamem', _fi() if tab == 1 else None), 
        ('offset: 00000000' if page else 'offset:      N/A', None) 
    )
    _draw_outline(
        win, 
        (mx, 14), (40, 8), _fw(), 
        ('progmem', _fi() if tab == 2 else None),
        ('offset: 00000044' if page else 'offset:      N/A', None)
    )


def task_bar(win, uart_model):
    w, h = _window_sz(win)
    y = h - 1

    _box(win, ' ', (0, y), (w, 1), _bw())

    if uart_model.dev:
        short_dev = uart_model.dev.split('/')[-1]
        ox = len(short_dev)
        wo = w - ox
        _txt(win, '■', (wo - 11, y), _tv() if uart_model.rxc & 1 else _tr())
        _txt(win, '■', (wo - 10, y), _tv() if uart_model.txc & 1 else _tt())
        _txt(win, f' uart: {short_dev}', (wo - 9, y), _bw())
    else:
        msg = 'uart disconnected'
        ox = len(msg)
        wo = w - ox
        _txt(win, f' {msg} ', (wo - 3, y), _bw())
        
    _txt(win, ' h ', (0, y), _bw())
    _txt(win, 'help msg ', (3, y), _tb())  
    _txt(win, ' s ', (12, y), _bw())
    _txt(win, 'save to  ', (15, y), _tb())
    _txt(win, ' l ', (24, y), _bw())
    _txt(win, 'latest   ', (27, y), _tb())
    _txt(win, ' q ', (36, y), _bw())
    _txt(win, 'quit     ', (39, y), _tb())


_mode_colors = {
    '(wait)': _my,
    'scroll': _mb,
    'latest': _mb,
    'freeze': _mb
}


def top_bar(win, page_model, acts):
    w, _ = _window_sz(win)
    _box(win, ' ', (0, 0), (w, 1), _tb())
    page_desc = f'page {page_model.now:4}/{page_model.top:4}'
    ox = len(page_desc)
    _txt(win, page_desc, (w - ox - 10, 0), _tb())

    mode = get_page_mode(page_model)
    color = _mode_colors.get(mode, _mb)()
    _txt(win, f' {mode} ', (w - 8, 0), color)

    _txt(win, ' Tab ', (1, 0), _tb())
    _txt(win, ' Nav ', (6, 0), _tb())
    
    x = 11
    for act in acts:
        text = f' {act} '
        _txt(win, text, (x, 0), _tb())
        x += len(text)


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
