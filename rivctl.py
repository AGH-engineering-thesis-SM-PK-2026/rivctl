import sys

from uart import next_page, open_uart
from data import (
    Page,
    open_db, save_db, save_one, find_by_ndx, count
)
from term import (
    popup, dialog, pager, abort, poll_user, ensure_vga, main_view, 
    task_bar, top_bar, run
)
from view import (
    UartModel, PageModel,
    flash_rx, reset_rx, upsert_page, follow_page, 
    move_to_page, jump_to_page, show, has_overlays, update_overlay
)
from msg_ import (
    readme_
)


_acts = [
    [],
    ['Find', '▲▼'],
    ['▲▼']
]


def see_cmdline_help():
    print(
        'rivctl.py [-h] [-r] FILE\n'
        '  control panel for debuging RISCV MCU\n'
        'options:\n'
        '  -h  show this help message\n'
        '  -r  indicates the FILE refers to saved .db file, otherwise\n'
        '      FILE is assumed to refer to serial console eg. /dev/ttyUSB0\n'
        '      on Linux or COM3 on Windows'
    )


def parse_args():
    is_tty = True
    filename = None
    _, *args = sys.argv
    for arg in args:
        if arg == '-h':
            see_cmdline_help()
            sys.exit(0)
        if arg == '-r':
            is_tty = False
            continue
    
        if filename is None:
            filename = arg

    return filename, is_tty


def loop(filename, is_tty, stdscr):
    stdscr.timeout(100)

    device = filename if is_tty else None
    stored = filename if not is_tty else None
    uart_model = UartModel(0, 0, device)
    page_model = PageModel(0, 0, True)
    tab = 0
    page = None

    def redraw_static():
        task_bar(stdscr, uart_model)
        top_bar(stdscr, page_model, _acts[tab])
        stdscr.refresh()

    try:
        if not filename:
            abort(
                stdscr,
                'fatal error',
                'path to serial console/capture file was not passed\n'
                'to capture debug packets use:\n'
                '  python rivctl.py /dev/ttyUSB0\n'
                'or view existing capture:\n'
                '  python rivctl.py -r capture.db'
            )

        with open_uart(device) as uart, open_db(stored) as db:
            top_ndx = count(db, Page)
            if top_ndx > 0:
                page_model = PageModel(1, top_ndx, False)
                page = find_by_ndx(db, Page, 1)

            def quit(_):
                sys.exit(0)

            def save_to_db(path):
                filename = f'{path}.db' if not path.endswith('.db') else path
                save_db(db, filename)
                return 'quit'

            def go_to_page(page):
                nonlocal page_model
                if page:
                    try:
                        page_model = jump_to_page(page_model, int(page))
                    except ValueError:
                        show(popup(
                            'bad page',
                            'page index should be an integer',
                            [('ok', None)]
                        ))
                        return 'ok'
                
                return 'quit'

            while True:
                ensure_vga(stdscr)

                page = find_by_ndx(db, Page, page_model.now)
                result, maybe_page = next_page(page_model.top, uart)
                if result != 'none':
                    uart_model = flash_rx(uart_model)
                else:
                    uart_model = reset_rx(uart_model)

                if maybe_page:
                    save_one(db, maybe_page)
                    page_model = upsert_page(page_model, maybe_page)
                
                ev, arg = poll_user(stdscr)
                if has_overlays():
                    update_overlay((ev, arg))
                elif ev == 'key':
                    assert isinstance(arg, str)
                    if arg == 'q':
                        show(popup(
                            'quit',
                            ' really quit?  ',
                            [('no', None), ('yes', quit)]
                        ))
                    if arg == 'h':
                        show(pager(
                            'help',
                            readme_,
                            (54, 15),
                            [('ok', None)]
                        ))
                    if arg == 's':
                        show(dialog(
                            'save to file',
                            'enter filename where for a .db file:',
                            [('cancel', None), ('save', save_to_db)]
                        ))
                    if arg == 'n':
                        show(dialog(
                            'jump',
                            'navigate to index:',
                            [('cancel', None), ('go', go_to_page)]
                        ))
                    if arg == 'tab':
                        if tab == 2:
                            tab = 0
                        else:
                            tab += 1
                    if arg == 'l':
                        page_model = follow_page(page_model)
                    main_view(stdscr, page, tab)
                elif ev == 'move':
                    assert isinstance(arg, tuple)
                    mx, _ = arg
                    page_model = move_to_page(page_model, mx)
                    main_view(stdscr, page, tab)
                else:
                    main_view(stdscr, page, tab)
                redraw_static()
                
    except OSError as e:
        abort(
            stdscr,
            'fatal error', 
            str(e).lower()
        )



def main():
    filename, is_tty = parse_args() 
    run(lambda scr: loop(filename, is_tty, scr))


if __name__ == '__main__':
    main()
