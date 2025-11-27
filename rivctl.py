import sys

from uart import (
    uart_recv, uart_emit, open_uart,
    send_halt, send_start, send_step, send_cycle, send_reset, send_prog
)
from data import (
    Page,
    open_db, save_db, save_one, find_by_ndx, count
)
from term import (
    popup, dialog, pager, menu, abort, poll_user, ensure_vga, main_view, 
    task_bar, top_bar, run
)
from view import (
    UartModel, PageModel, ModeModel,
    flash_rx, reset_rx, flash_tx, reset_tx, upsert_page, follow_page, 
    move_to_page, jump_to_page, show, has_overlays, update_overlay, 
    update_mode, to_halt_mode, to_run_mode, to_step_mode, to_reset_mode, to_upload_mode
)
from msg_ import (
    readme_, no_file_dev_
)


_acts = [
    ['File', 'Page'],
    ['File', 'Page', '▲▼'],
    ['File', 'Page', '▲▼']
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
    mode_model = ModeModel('empty*', 'ready*')
    tab = 0
    page = None

    def redraw_static():
        task_bar(stdscr, uart_model)
        top_bar(stdscr, mode_model, page_model, _acts[tab])
        stdscr.refresh()

    try:
        if not filename:
            abort(
                stdscr,
                'No File/Device',
                no_file_dev_
            )

        with open_uart(device) as uart, open_db(stored) as db:
            top_ndx = count(db, Page)
            if top_ndx > 0:
                page_model = PageModel(1, top_ndx, False)
                page = find_by_ndx(db, Page, 1)

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

            def show_quit():
                show(popup(
                    'Quit',
                    ' Really quit?  ',
                    [('no', None), ('yes', lambda _: sys.exit(0))]
                ))

            def show_help():
                show(pager(
                    'Help',
                    readme_,
                    (54, 15),
                    [('ok', None)]
                ))

            def show_save():
                show(dialog(
                    'Save As',
                    'Enter session filename:                 ',
                    [('cancel', None), ('save', save_to_db)]
                ))
            
            def show_jump():
                show(dialog(
                    'Jump Tos',
                    'Navigate to index:',
                    [('cancel', None), ('go', go_to_page)]
                ))

            def to_latest():
                nonlocal page_model
                page_model = follow_page(page_model)

            while True:
                ensure_vga(stdscr)

                page = find_by_ndx(db, Page, page_model.now)

                what, value = uart_recv(uart)
                if what == 'none':
                    if value:
                        uart_model = flash_rx(uart_model)
                    else:
                        uart_model = reset_rx(uart_model)
                elif what == 'page':
                    assert isinstance(value, tuple)
                    page = Page(page_model.top, *value)
                    save_one(db, page)
                    page_model = upsert_page(page_model, page)

                if uart_emit(uart):
                    uart_model = flash_tx(uart_model)
                else:
                    uart_model = reset_tx(uart_model)
                
                mode_model = update_mode(mode_model, page_model)

                ev, arg = poll_user(stdscr)
                if has_overlays():
                    update_overlay((ev, arg))
                elif ev == 'key':
                    assert isinstance(arg, str)
                    if arg == 'Q':
                        show_quit()
                    if arg == 'H':
                        show_help()
                    if arg == 'S':
                        show_save()
                    if arg == 'U':
                        # show_upload()
                        pass
                    if arg == 'N':
                        show_jump()
                    if arg == 'L':
                        to_latest()
                    if arg == 'tab':
                        if tab == 2:
                            tab = 0
                        else:
                            tab += 1
                    if arg == 'F':
                        show(menu(
                            (1, 1), 
                            [
                                ('Save As ...', lambda _: show_save()),
                                ('Upload ...', None),
                                ('-', None),
                                ('Help', lambda _: show_help()),
                                ('Quit', lambda _: show_quit())
                            ]
                        ))
                    if arg == 'P':
                        show(menu(
                            (7, 1),
                            [
                                ('To Page ...', lambda _: show_jump()),
                                ('Latest', lambda _: to_latest())
                            ]
                        ))
                    if arg == 'h':
                        mode_model = to_halt_mode(mode_model)
                        send_halt()
                    if arg == 'z':
                        mode_model = to_run_mode(mode_model)
                        send_start()
                    if arg == 'a':
                        mode_model = to_step_mode(mode_model)
                        send_cycle()
                    if arg == 's':
                        mode_model = to_step_mode(mode_model)
                        send_step()
                    if arg == 'r':
                        mode_model = to_reset_mode(mode_model)
                        send_reset()
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
