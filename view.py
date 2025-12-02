from collections import namedtuple


class UartModel(namedtuple('UartModel', 'rxc txc dev')):
    def flash_rx(self):
        return UartModel(self.rxc + 1, self.txc, self.dev)  

    def reset_rx(self):
        return UartModel(0, self.txc, self.dev)  

    def flash_tx(self):
        return UartModel(self.rxc, self.txc + 1, self.dev)  

    def reset_tx(self):
        return UartModel(self.rxc, 0, self.dev)  


class PageModel(namedtuple('PageModel', 'now top follow print')):
    def upsert_page(self, page):
        top = page.ndx
        if self.follow or self.now == 0:
            return PageModel(top, top, self.follow, self.print)

        return PageModel(self.now, top, self.follow, self.print)

    def to_follow(self):
        return PageModel(self.top, self.top, True, self.print)

    def move_to(self, move_by):
        if self.top == 0:
            return PageModel(0, self.top, self.follow, self.print)
        now = max(min(self.now + move_by, self.top), 1)
        return PageModel(now, self.top, False, self.print)

    def jump_to(self, ndx):
        if ndx > 0:
            now = min(ndx, self.top)
            return PageModel(now, self.top, False, self.print)
        elif ndx < 0:
            now = max(self.now + ndx, 1)
            return PageModel(now, self.top, False, self.print)
        
        return self

    @property
    def mode(self):
        if self.top == 0:
            return '(wait)'
        if self.follow:
            return 'latest'
        return 'scroll'


_run1 = '<*   >'
_run2 = '< *  >'
_run3 = '<  * >'
_run4 = '<   *>'
_1step1 = '1step*'
_1step2 = '1step '
_cycle1 = 'cycle*'
_cycle2 = 'cycle '


class ModeModel(namedtuple('ModeModel', 'page ctl')):
    def update(self, page_model):
        page = page_model.mode
        if self.ctl == _run1:
            return ModeModel(page, _run2)
        if self.ctl == _run2:
            return ModeModel(page, _run3)
        if self.ctl == _run3:
            return ModeModel(page, _run4)
        if self.ctl == _run4:
            return ModeModel(page, _run1)
        if self.ctl == _1step1:
            return ModeModel(page, _1step2)
        if self.ctl == _cycle1:
            return ModeModel(page, _cycle2)
        return ModeModel(page, self.ctl)

    def to_halt(self):
        return ModeModel(self.page, 'halted')

    def to_run(self):
        return ModeModel(self.page, '< *  >')

    def to_1step(self):
        return ModeModel(self.page, '1step*')

    def to_cycle(self):
        return ModeModel(self.page, 'cycle*')

    def to_reset(self):
        return self

    def to_upload(self):
        return ModeModel(self.page, 'upload')


class Overlays:
    def __init__(self):
        self._stack = []

    def show(self, overlay):
        if len(self._stack) > 0:
            _, _, last_close = self._stack.pop()
            last_close()
        redraw, update, close, *misc = overlay
        self._stack.append((redraw, update, close))
        return misc

    @property
    def has_any(self):
        return len(self._stack) > 0;

    def update(self, poll_result):
        _, update, close = self._stack[-1]
        if update(poll_result) == 'quit':
            close()
            self._stack.pop()
        # in case update replaced overlay, won't redraw old window
        if self.has_any:
            redraw_overlay, _, _ = self._stack[-1]
            redraw_overlay()
