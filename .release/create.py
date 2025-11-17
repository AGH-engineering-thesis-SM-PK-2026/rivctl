import sys
import shutil
import subprocess

import lmsg


def _hi(text):
    return f'| {text}'


_ignored = shutil.ignore_patterns(
    '__pycache__',
    '.venv',
    '.git',
    '*.pyz'
)


def copy_files(where):
    print(_hi('Copy files...'))
    shutil.copytree('.', where, ignore=_ignored)


def update_files(where, tag):
    print(_hi('Create main file entry __main__.py'))
    with open(f'{where}/__main__.py', 'w', encoding='utf-8') as fp:
        fp.write(
            'import rivctl\n\n'
            f'# release {tag}\n\n'
            'if __name__ == \'__main__\':\n'
            f'  print(\'rivctl {tag}\')\n'
            '  rivctl.main()\n'
        )
    print(_hi('Update msg_.py'))
    with open(f'{where}/.release/lmsg.txt', encoding='utf-8') as src_fp:
        msgs = lmsg.read_local_msg(src_fp)
        msgs['readme'] += f'        rivctl.py {tag}\n'
        with open(f'{where}/msg_.py', 'w', encoding='utf-8') as py_fp:
            lmsg.write_local_msg_py(py_fp, msgs)


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
    if len(sys.argv) != 2:
        print('python create.py <TAG>')
        sys.exit(1)
    _, tag = sys.argv
    ver = tag.replace('.', '')
    where = f'rivctl_{ver}'
    try:
        copy_files(where)
        update_files(where, tag)
        install_deps(where)
        build_archive(where)
        print(_hi('Done'))
        sys.exit(0)
    finally:
        cleanup(where)
