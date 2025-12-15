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
grwh = def_color(curses.COLOR_GREEN, curses.COLOR_WHITE)
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


class Window:
    def __init__(self, win):
        self._win = win
        
    @classmethod
    def of(cls, title, sz, pos=(0, 0), keypad=False, fg=bkwh):
        w, h = sz
        x, y = pos
        try:
            win = cls(curses.newwin(h, w, y, x))
            win._prep(fg, keypad)
            if title:
                win.txt(f' {title} ', (_hp, 0), fg())
            return win
        except CursesError:
            raise WindowError('invalid window pos/size')

    @property
    def size(self):
        y, x = self._win.getmaxyx()
        return x, y

    def bg(self, color):
        self._win.clear()
        self._win.bkgd(' ', color)

    def txt(self, text, pos, color):
        x, y = pos
        self._win.addstr(y, x, text, color)

    def box(self, char, pos, size, color):
        x, y = pos
        w, h = size
        self._win.attron(color)
        for v in range(y, y + h):
            self._win.hline(v, x, char, w)
        self._win.attroff(color)

    def _prep(self, fg, keypad):
        self._win.attron(fg())
        self._win.box()
        self._win.attroff(fg())
        self._win.keypad(keypad)
        self._win.bkgd(' ', fg())

    def with_timeout(self, ms):
        self._win.timeout(ms)

    def draw_btns(self, btns, y, sel):
        labels = [f'  {label}  ' for label, _ in btns]

        w, _ = self.size
        wbtn = sum([len(label) + _hp for label in labels])
        x = w - wbtn
        for i, label in enumerate(labels):
            color = cybk() if sel == i else cywh()
            self.txt(label, (x, y), color)
            x += len(label) + _hp

    def draw_input(self, text, y, focus):
        w, _ = self.size
        wi = w - _hp*2
        cut = text[-wi+1:]

        color = cybk() if focus else whbk()
        pos = (_hp, y)
        self.box(' ', pos, (wi, 1), color)
        self.txt(cut, pos, color)
        if focus:
            self.txt('█', (len(cut) + _hp, y), color)

    def draw_outline(self, pos, sz, color, title=None, label=None):
        x, y = pos
        w, h = sz
        top = '┌' + '─' * w + '┐'
        bottom = '└' + '─' * w + '┘'
        self.txt(top, (x - 1, y - 1), color)
        self.txt(bottom, (x - 1, y + h), color)
        for v in range(y, y + h):
            self.txt('│', (x - 1, v), color)
            self.txt('│', (x + w, v), color)
        if title:
            title_text, title_color = title
            self.txt(f' {title_text} ', (x, y - 1), title_color or color)
        if label:
            label_text, label_color = label
            u = x + w - len(label_text) - 4
            self.txt(f' {label_text} ', (u, y + h), label_color or color)

    def draw_scroll_bar(self, pos, h, r, pct, color):
        x, y = pos
        t = int(pct * 0.99 * (h - r * 2)) + r
        for v in range(h):
            track = v >= t - r and v <= t + r
            self.txt('█' if track else '│', (x, v + y), color)
    
    def poll(self):
        key = self._win.getch()
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

    def refresh(self):
        self._win.refresh()

    def erase(self):
        self._win.erase()

    def close(self):
        self._win.erase()
        del self._win


class Toast(Window):
    def __init__(self, title, message, hx=0):
        lines = message.split('\n')
        w = max([len(line) for line in lines]) + _hp*2
        h = len(lines) + 5 + hx
        
        win = Window.of(title, (w, h), (2, 2), keypad=True)
        super().__init__(win._win)

        for i, line in enumerate(lines):
            self.txt(line, (_hp, i + 2), bkwh())


def popup(title, message, btns):
    win = Toast(title, message)
    _, h = win.size

    accept_ev = False
    btn_sel = len(btns) - 1

    def redraw():
        win.draw_btns(btns, h - 2, btn_sel)
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
    win = Toast(title, message, 1)
    _, h = win.size

    accept_ev = False
    input_sel = True
    btn_sel = len(btns) - 1
    text = ''

    def redraw():
        win.draw_input(text, h - 4, input_sel)
        win.draw_btns(btns, h - 2, btn_sel if not input_sel else -1)
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
    win = Window.of(title, (vw + 3, vh + 5), (2, 2), keypad=True)
    w, h = win.size

    accept_ev = False
    row = 0
    btn_sel = len(btns) - 1

    def redraw():
        for i in range(row, row+vh):
            y = i - row + 2
            win.box(' ', (_hp, y), (vw - 1, 1), fg())
            try:
                win.txt(lines[i][:vw - 6], (_hp, y), fg())
            except IndexError:
                pass
        if bottom > 0:
            win.draw_scroll_bar((w - 3, 2), vh, 1, row / bottom, fg())
        win.draw_btns(btns, h - 2, btn_sel)
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

    win = Window.of(None, (w, h), pos, fg=whcy)

    accept_ev = False
    act_sel = 0

    def _draw_acts(y, sel):
        for i, (text, _) in enumerate(acts):
            if text == '-':
                
                line = '─' * (w - 2)
                win.txt(f'├{line}┤', (0, y + i), whcy())
            else:
                color = cybk() if i == sel else whcy()
                win.txt(text, (1, y + i), color)

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


def _cycle(items, from_index):
    if len(items):
        yield from []
    index = from_index
    while True:
        if index >= len(items):
            index = 0
        yield items[index]


def picker(title, message, sz, act, fc=whbk, dc=cybk, sc=bkcy, init='.'):
    vw, vh = sz

    # empty message, will be drawn later
    win = Window.of(title, (vw + 3, vh + 5), (2, 2), keypad=True)
    w, h = win.size

    accept_ev = False
    row = 0
    sel = 0

    path = pathlib.Path(init)
    items = []

    def redraw():
        bottom = len(items) - vh
        for i in range(row, row+vh):
            y = i - row + 2
            win.box(' ', (_hp, y), (vw - 1, 1), fc())
            try:
                item = items[i]
                name = f'-{item.name}/' if item.is_dir() else f'-{item.name}'
                if i == sel:
                    win.txt(name[:vw-6], (_hp, y), sc())
                else:
                    color = dc() if item.is_dir() else fc()
                    win.txt(name[:vw-6], (_hp, y), color)
            except IndexError:
                pass
        if bottom > 0:
            win.draw_scroll_bar((w - 3, 2), vh, 1, row / bottom, fc())
        win.txt(message[w-4:], (3, h - 3), fc())
        win.refresh()

    def _get_parent(p):
        return p.joinpath(pathlib.Path('..'))

    def _path_to_items(p):
        parent = _get_parent(p)
        items = list(p.glob('*'))
        dirs = filter(lambda item: item.is_dir(), items)
        files = filter(lambda item: not item.is_dir(), items)
        return [parent] + list(dirs) + list(files)

    def update(poll):
        nonlocal path, items, accept_ev, row, sel
        ev, arg = poll
        items = _path_to_items(path)
        bottom = len(items) - vh
        cnt = vh // 2
        if not accept_ev:
            if ev == 'empty':
                accept_ev = True
        elif ev == 'move':
            assert isinstance(arg, tuple)
            _, my = arg
            max_sel = len(items) - 1
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
                    sel = 0
                    row = max(min(sel - cnt, bottom), 0)
                    return 'ok'
                return act(item)
            elif arg == 'del':
                path = _get_parent(path)
                sel = 0
                row = max(min(sel - cnt, bottom), 0)
            else:
                entries = list(enumerate(items))
                for i, item in entries[sel+1:] + entries[:sel]:
                    if item.name.startswith(arg):
                        sel = i
                        row = max(min(sel - cnt, bottom), 0)
                        break
        return 'ok'

    def close():
        win.erase()    

    return redraw, update, close


def progress(title, vw, pb=grwh):
    # empty message, will be drawn later
    win = Window.of(title, (vw + 8, 6), (2, 2), keypad=True)
    progress = 0.0
    timeout = 4

    def on_progress(new_progress):
        nonlocal progress
        progress = new_progress

    def redraw():
        pct = int(progress * 100)
        pw = min(int(progress * vw), vw)
        bw = vw - pw
        win.txt('■' * pw, (2, 2), pb())
        win.txt('■' * bw, (2 + pw, 2), bkwh())
        win.txt(f' {pct:3}%', (vw, 2), pb())
        win.draw_btns([('hide', lambda _: _)], 4, 0)
        win.refresh()

    def update(poll):
        nonlocal timeout
        ev, arg = poll
        if timeout <= 0:
            return 'quit'
        if progress == 1.0:
            timeout -= 1
        if ev == 'key':
            assert isinstance(arg, str)
            if arg == 'esc' or arg == 'enter' or arg == 'q':
                return 'quit'
        return 'ok'

    def close():
        win.erase()

    return redraw, update, close, on_progress


def abort(win, title, message, exc_creator):
    win.bg(whbl())

    try:
        redraw, update, _ = popup(title, message, [('exit', None)])
        while update(win.poll()) != 'quit':
            redraw()
    except WindowError:
        print(f'exit: {title}')
        for line in message.split('\n'):
            print(f'  {line}')
    raise exc_creator()


def ensure_vga(win):
    w, h = win.size
    if h < 24 or w < 80:
        abort(
            win, 
            'Bad Size', 
            'Terminal size must be at least 80x24',
            lambda: WindowError('too small window')
        )


_regs_names = [
    'zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2',
    's0', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
    'a6', 'a7', 's2', 's3', 's4', 's5', 's5', 's7',
    's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6'
]


def main_view(win, page, prog, tab):
    win.bg(whbl())

    rx = 2
    mx = 38
    oy = 4

    if page:
        regs_vals = page.regs.split(',')[:32]
        win.txt('pc    ', (rx + 1, oy), yebl())
        win.txt(f'{page.pc:8}', (rx + 7, oy), whbl())
        for i, reg_name, reg_val in zip(range(32), _regs_names, regs_vals):
            x = (0 if i < 16 else 16) + rx + 1
            y = i % 16 + oy + 2
            win.txt(f'{reg_name:6}', (x, y), yebl())
            win.txt(f'{reg_val:8}', (x + 6, y), whbl())
    else:
        win.txt('no pages yet', (rx + 2, 6), whbl())

    if page:
        data_vals = ['00000000'] * 32
        for i, data_val in zip(range(32), data_vals):
            x = i % 4 * 10 + mx + 1
            y = i // 4 + oy
            win.txt(f'{data_val:8}', (x, y), whbl())
    else:
        win.txt('no pages yet', (mx + 2, 6), whbl())

    if page:
        ndx = int(page.pc, 16) // 4;
        for i in range(8):
            y = i + oy + 10
            if ndx + i < len(prog):
                prog_val = prog[ndx + i]
                if (i == 0):
                    win.txt('>', (mx, y), yebl())
                loc = f'{prog_val.loc.upper():>08}'
                src = prog_val.src[:24]
                win.txt(loc, (mx + 1, y), yebl())
                win.txt(src, (mx + 11, y), whbl())

                # _txt(win, f'{mnemo:6}{params}', (mx + 11, y), whbl())
            else:
                win.txt('--------', (mx + 1, y), yebl())
                win.txt('-', (mx + 11, y), whbl())
    else:
        win.txt('no pages yet', (mx + 2, 16), whbl())
        
    win.draw_outline(
        (rx, 4), (32, 18), whbl(), 
        ('regfile', None)
    )
    win.draw_outline(
        (mx, 4), (40, 8), whbl(),
        ('datamem', None), 
        ('offset: 00000000' if page else 'offset:      N/A', None) 
    )
    win.draw_outline(
        (mx, 14), (40, 8), whbl(), 
        ('progmem', None),
        ('offset: 00000044' if page else 'offset:      N/A', None)
    )


def task_bar(win, uart_model):
    w, h = win.size
    y = h - 1

    win.box(' ', (0, y), (w, 1), whbk())

    if uart_model.dev:
        short_dev = uart_model.dev.split('/')[-1]
        ox = len(short_dev)
        wo = w - ox
        win.txt('■', (wo - 11, y), bkbk() if uart_model.rxc & 1 else grbk())
        win.txt('■', (wo - 10, y), bkbk() if uart_model.txc & 1 else yebk())
        win.txt(f' <-> {short_dev}', (wo - 9, y), whbk())
    else:
        msg = ' <-> <nil>'
        ox = len(msg)
        wo = w - ox
        win.txt(f' {msg} ', (wo - 9, y), whbk())
        
    def _draw_hint(key, hint, x):
        win.txt(f' {key} ', (x, y), whbk())
        win.txt(f'{hint:<7}', (x+3, y), bkcy())  

    _draw_hint('h', 'Halt', 0)
    _draw_hint('z', 'Run', 10)
    _draw_hint('a', 'Cycle', 20)
    _draw_hint('s', 'Step', 30)
    _draw_hint('r', 'Reset', 40)


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
    w, _ = win.size
    win.box(' ', (0, 0), (w, 1), bkcy())
    page_desc = f'page {page_model.now:4}/{page_model.top:4}'
    ox = len(page_desc)
    win.txt(page_desc, (w - ox - 10, 0), bkcy())

    color = _ctl_mode_colors.get(mode_model.ctl, cybk)()
    win.txt(f' {mode_model.ctl} ', (w - 8, 0), color)

    def _draw_btn(text, x):
        win.txt(text, (x + 1, 0), bkcy())
        return x + len(text) + 2

    x = 1
    for act in acts:
        x = _draw_btn(act, x)


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
