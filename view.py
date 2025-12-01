from collections import namedtuple


UartModel = namedtuple('UartModel', 'rxc txc dev')
PageModel = namedtuple('PageModel', 'now top follow always_print')
ModeModel = namedtuple('ModeModel', 'page ctl')


def flash_rx(uart_model):
    rx, tx, dev = uart_model
    return UartModel(rx + 1, tx, dev)  


def reset_rx(uart_model):
    _, tx, dev = uart_model
    return UartModel(0, tx, dev)  


def flash_tx(uart_model):
    rx, tx, dev = uart_model
    return UartModel(rx, tx + 1, dev)  


def reset_tx(uart_model):
    rx, _, dev = uart_model
    return UartModel(rx, 0, dev)  


def upsert_page(page_model, page):
    now, _, follow, always_print = page_model
    top = page.ndx
    if follow or now == 0:
        return PageModel(top, top, follow, always_print)

    return PageModel(now, top, follow, always_print)


def follow_page(page_model):
    _, top, _, always_print = page_model
    return PageModel(top, top, True, always_print)


def move_to_page(page_model, move_by):
    now, top, _, always_print = page_model
    return PageModel(
        max(min(now + move_by, top), 1), 
        top, 
        False, 
        always_print
    )


def jump_to_page(page_model, ndx):
    now, top, _, always_print = page_model
    if ndx > 0:
        return PageModel(min(ndx, top), top, False, always_print)
    elif ndx < 0:
        return PageModel(max(now + ndx, 1), top, False, always_print)


def get_page_mode(page_model):
    if page_model.top == 0:
        return '(wait)'
    if page_model.follow:
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


def update_mode(mode_model, page_model):
    page = get_page_mode(page_model)
    _, ctl = mode_model
    if ctl == _run1:
        return ModeModel(page, _run2)
    if ctl == _run2:
        return ModeModel(page, _run3)
    if ctl == _run3:
        return ModeModel(page, _run4)
    if ctl == _run4:
        return ModeModel(page, _run1)
    if ctl == _1step1:
        return ModeModel(page, _1step2)
    if ctl == _cycle1:
        return ModeModel(page, _cycle2)
    return ModeModel(page, ctl)


def to_halt_mode(mode_model):
    page, _ = mode_model
    return ModeModel(page, 'halted')


def to_run_mode(mode_model):
    page, _ = mode_model
    return ModeModel(page, '< *  >')


def to_1step_mode(mode_model):
    page, _ = mode_model
    return ModeModel(page, '1step*')


def to_cycle_mode(mode_model):
    page, _ = mode_model
    return ModeModel(page, 'cycle*')


def to_reset_mode(mode_model):
    return mode_model


def to_upload_mode(model_model):
    page, _ = model_model
    return ModeModel(page, 'upload')


_stack = []


def show(overlay):
    if len(_stack) > 0:
        _, _, close = _stack.pop()
        close()
    _stack.append(overlay)


def has_overlays():
    return len(_stack) > 0;


def update_overlay(poll):
    _, update, close = _stack[-1]
    if update(poll) == 'quit':
        close()
        _stack.pop()
    # in case update replaced overlay, won't redraw old window
    if has_overlays():
        redraw_overlay, _, _ = _stack[-1]
        redraw_overlay()
