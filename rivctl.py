import sys

from app import App, AppExit
from term import run
import msg_ as m


def see_usage():
    print(m.usage_)


def parse_args():
    is_tty = True
    filename = None
    _, *args = sys.argv
    for arg in args:
        if arg == '-h':
            see_usage()
            sys.exit(0)
        if arg == '-r':
            is_tty = False
            continue
    
        if filename is None:
            filename = arg

    return filename, is_tty


def loop(scr, filename, is_tty):
    try:
        app = App(scr, filename, is_tty)
        app.loop()
    except AppExit:
        sys.exit(0)

def main():
    filename, is_tty = parse_args() 
    run(lambda scr: loop(scr, filename, is_tty))


if __name__ == '__main__':
    main()
