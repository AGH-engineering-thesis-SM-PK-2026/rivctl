import sys
from file import read_prog
import msg_ as m

from uart import Uart, UartPacketIn
from data import (
    Db, Instr, Page
)
from term import (
    Window, abort, dialog, ensure_vga, main_view, menu, pager, picker, popup, progress, task_bar, top_bar, whbk
)
from view import (
    ModeModel, Overlays, PageModel, UartModel
)


class AppExit(Exception):
    pass


class App:
    def __init__(self, scr, filename, is_tty):
        self.win = Window(scr)
        self.win.with_timeout(100)

        self.views = Overlays()

        self.device = filename if is_tty else None
        self.stored = filename if not is_tty else None

        if not filename:
            abort(
                self.win,
                m.no_file_dev_,
                m.no_file_dev_text_,
                lambda: RuntimeError('no filename')
            )

        self.uart_model = UartModel(0, 0, self.device)
        self.page_model = PageModel(0, 0, True, True)
        self.mode_model = ModeModel('empty*', 'ready*')

        if self.device:
            self.uart = Uart.open(self.device)
        else:
            self.uart = Uart.null()
        if self.stored:
            self.db = Db.to_file(self.stored)
        else:
            self.db = Db.in_memory()

    def _redraw_static(self):
        task_bar(self.win, self.uart_model)
        top_bar(self.win, self.mode_model, self.page_model, ['File', 'Page'])
        self.win.refresh()


    def _save_to_db(self, path):
        filename = f'{path}.db' if not path.endswith('.db') else path
        self.db.save_db(filename)
        return 'quit'

    def _go_to_page(self, page):
        if page:
            try:
                self.page_model = self.page_model.jump_to(int(page))
            except ValueError:
                self.views.show(popup(
                    m.bad_page_,
                    m.bad_page_text_,
                    [('ok', None)]
                ))
                return 'ok'
        
        return 'quit'

    def _show_quit(self):
        def _quit(_):
            raise AppExit('quit')

        self.views.show(popup(
            m.quit_,
            m.quit_text_,
            [(m.no_, None), (m.yes_, _quit)]
        ))

    def _show_help(self):
        self.views.show(pager(
            m.help_,
            m.readme_,
            (53, 15),
            [('ok', None)]
        ))

    def _show_save(self):
        self.views.show(dialog(
            m.save_as_,
            m.save_as_text_,
            [(m.cancel_, None), ('save', self._save_to_db)]
        ))
    
    def _show_jump(self):
        self.views.show(dialog(
            m.jump_to_,
            m.jump_to_text_,
            [(m.cancel_, None), ('go', self._go_to_page)]
        ))

    def _to_latest(self):
        self.page_model = self.page_model.to_follow()

    def _show_upload_bad_file(self):
        self.views.show(popup(
            m.bad_prog_file_,
            m.bad_prog_file_text_,
            [('ok', None)]
        ))
    
    def _show_upload_preview(self, dump):
        instrs = list(dump)

        text = '\n'.join(
            [f'{l:>6}:  {c}    {s}' for l, c, s in instrs] +
            ['.']
        )

        def _upload(_):
            self.mode_model = self.mode_model.to_upload()
            self.db.drop_all(Instr)
            for instr in instrs:
                self.db.save_one(instr)

            _on_send, = self.views.show(progress(m.uploading_, 20))

            self.uart.send_prog([instr.code for instr in instrs], _on_send)
            return 'ok'
        
        self.views.show(pager(
            m.upload_preview_,
            text,
            (73, 15),
            [(m.cancel_, None), ('upload', _upload)], 
            whbk
        ))

    def _show_upload(self):
        def parse_program(path):
            try:
                self._show_upload_preview(read_prog(path))
            except IOError:
                self._show_upload_bad_file()

        self.views.show(picker(
            m.upload_,
            m.upload_hint_,
            (53, 5),
            parse_program
        ))

    def loop(self):
        try:
            top_ndx = self.db.count(Page)
            if top_ndx > 0:
                self.page_model = PageModel(1, top_ndx, False, True)
                page = self.db.find_by_ndx(Page, 1)

            while True:
                ensure_vga(self.win)

                page = self.db.find_by_ndx(Page, self.page_model.now)

                value = self.uart.receive()
                if type(value) is int:
                    if value > 0:
                        self.uart_model = self.uart_model.flash_rx()
                    else:
                        self.uart_model = self.uart_model.reset_rx()
                elif type(value) is UartPacketIn:
                    data = value.data.decode(encoding='ascii')
                    pc, regs = data.strip('P\n').split(',', 1)
                    page = Page(self.page_model.top + 1, pc, f'00000000,{regs}')
                    self.db.save_one(page)
                    self.page_model = self.page_model.upsert_page(page)

                if self.uart.send():
                    self.uart_model = self.uart_model.flash_tx()
                else:
                    self.uart_model = self.uart_model.reset_tx()
                
                self.mode_model = self.mode_model.update(self.page_model)

                ev, arg = self.win.poll()
                if self.views.has_any:
                    self.views.update((ev, arg))
                elif ev == 'key':
                    assert isinstance(arg, str)
                    if arg == 'Q':
                        self._show_quit()
                    if arg == 'H':
                        self._show_help()
                    if arg == 'S':
                        self._show_save()
                    if arg == 'U':
                        self._show_upload()
                    if arg == 'N':
                        self._show_jump()
                    if arg == 'L':
                        self._to_latest()
                    if arg == 'F':
                        self.views.show(menu(
                            (1, 1), 
                            [
                                (
                                    f'{m.save_as_} ...', 
                                    lambda _: self._show_save()
                                ),
                                (
                                    f'{m.upload_} ...', 
                                    lambda _: self._show_upload()
                                ),
                                ('-', None),
                                (
                                    f'{m.help_}', 
                                    lambda _: self._show_help()
                                ),
                                (
                                    f'{m.quit_}', 
                                    lambda _: self._show_quit()
                                )
                            ]
                        ))
                    if arg == 'P':
                        self.views.show(menu(
                            (7, 1),
                            [
                                (
                                    f'{m.to_page_} ...', 
                                    lambda _: self._show_jump()
                                ),
                                (
                                    f'{m.latest_}', 
                                    lambda _: self._to_latest()
                                )
                            ]
                        ))
                    if arg == 'h' or arg == 'p':
                        self.mode_model = self.mode_model.to_halt()
                        self.uart.send_halt()
                        self.uart.send_print()
                    if arg == 'z':
                        self.mode_model = self.mode_model.to_run()
                        self.uart.send_start()
                    if arg == 'a':
                        self.mode_model = self.mode_model.to_cycle()
                        self.uart.send_cycle()
                        self.uart.send_print()
                    if arg == 's':
                        self.mode_model = self.mode_model.to_1step()
                        self.uart.send_step()
                        self.uart.send_print()
                    if arg == 'r':
                        self.mode_model = self.mode_model.to_reset()
                        self.uart.send_reset()
                    main_view(self.win, page, self.db.find_all(Instr), 0)
                elif ev == 'move':
                    assert isinstance(arg, tuple)
                    mx, _ = arg
                    self.page_model = self.page_model.move_to(mx)
                    main_view(self.win, page, self.db.find_all(Instr), 0)
                else:
                    main_view(self.win, page, self.db.find_all(Instr), 0)
                self._redraw_static()
        finally:
            self.uart.close()
            self.db.close()
