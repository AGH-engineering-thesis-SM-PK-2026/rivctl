class LocalMsgNameError(Exception):
    pass


def read_local_msg(fp):
    msgs = {}
    key = None
    for line in fp.readlines():
        item = line.rstrip()
        if item == '.':
            key = None
        elif item.startswith('#'):
            # a comment
            pass
        elif key:
            msgs[key] = msgs.get(key, '') + line
        elif item.startswith('[') and item.endswith(']'):
            maybe_key = item[1:-1]
            if not maybe_key.isidentifier():
                raise LocalMsgNameError(
                    f'\'{maybe_key}\' is not a valid lmsg identifier'
                )
            key = maybe_key

    return msgs


def write_local_msg_py(fp, msgs):
    fp.write('# generate by lmsg\n')
    for key, text in msgs.items():
        fp.write('\n\n')
        # add '_' after var name
        fp.write(f'{key}_ = \'\'\'')
        fp.write(text)
        fp.write('\'\'\'\n')
