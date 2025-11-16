import sys
import shutil
import subprocess


_hi = lambda text: f'\x1b[1;35m{text}\x1b[0m'

_ignored = shutil.ignore_patterns(
    '__pycache__',
    '.venv',
    '.git',
    '*.pyz'
)


def copy_files(where):
    print(_hi('Copy files...'))
    shutil.copytree('.', where, ignore=_ignored)


def create_main_file(where, tag):
    print(_hi('Create main file entry'))
    with open(f'{where}/__main__.py', 'w') as fp:
        fp.write(
            'import rivctl\n\n'
            f'# release {tag}\n\n'
            'if __name__ == \'__main__\':\n'
            f'  print(\'rivctl {tag}\')\n'
            '  rivctl.main()\n'
        )


def install_deps(where):
    print(_hi('Install dependencies'))
    subprocess.run([
        sys.executable,
        '-m', 'pip', 'install',
        '-r', 'requirements.txt',
        '--target', where
    ])


def build_archive(where):
    print(_hi(f'Build {where}.pyz'))
    subprocess.run([
        sys.executable,
        '-m', 'zipapp', where
    ])


def cleanup(where):
    try:
        shutil.rmtree(where)
    except FileNotFoundError:
        pass


if __name__ == '__main__':
    try:
        _, tag = sys.argv
        ver = tag.replace('.', '')
        where = f'rivctl_{ver}'
        cleanup(where)
        copy_files(where)
        create_main_file(where, tag)
        install_deps(where)
        build_archive(where)
        cleanup(where)
        print(_hi('Done'))
        sys.exit(0)
    except ValueError:
        print('python create.py <TAG>')
        sys.exit(1)
