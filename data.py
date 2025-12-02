import sqlite3

from collections import namedtuple


Page = namedtuple('Page', 'ndx pc regs')
Instr = namedtuple('Instr', 'loc code src')
Diff = namedtuple('Diff', 'ndx regs')

_EntSpec = namedtuple(
    '_EntSpec',
    'table fields init find_all find_ndx count save drop_all drop_ndx'
)


_specs = {}


def _get_spec(con, ent_type):
    return _specs.get(ent_type) or _create_spec(con, ent_type)


def _create_spec(con, ent_type):
    table = ent_type.__name__
    fields = ent_type._fields
    field_arg = ','.join('?' * len(fields))
    field_def = ','.join(fields)

    init = f'CREATE TABLE IF NOT EXISTS {table}({field_def})'
    find_all = f'SELECT {field_def} FROM {table}'
    find_ndx = f'SELECT {field_def} FROM {table} WHERE ndx = ?'
    count = f'SELECT COUNT(*) FROM {table}'
    save = f'INSERT INTO {table} VALUES ({field_arg})'
    drop_all = f'DELETE FROM {table}'
    drop_ndx = f'DELETE FROM {table} WHERE ndx = ?'

    ent_spec = _EntSpec(
        table, fields, init, 
        find_all, find_ndx, 
        count, save,
        drop_all, drop_ndx
    )

    cur = con.cursor()
    cur.execute(ent_spec.init)

    _specs[ent_type] = ent_spec
    return ent_spec


class Db:
    def __init__(self, con):
        self._con = con

    @classmethod
    def to_file(cls, filename):
        return Db(sqlite3.connect(filename))

    @classmethod
    def in_memory(cls):
        return Db(sqlite3.connect(':memory:'))

    def save_one(self, ent):
        ent_spec = _get_spec(self._con, type(ent))

        cur = self._con.cursor()
        cur.execute(ent_spec.save, tuple(ent))
        self._con.commit()

    def drop_all(self, ent_type):
        ent_spec = _get_spec(self._con, ent_type)

        cur = self._con.cursor()
        cur.execute(ent_spec.drop_all)
        self._con.commit()

    def drop_by_ndx(self, ent_type, ndx):
        ent_spec = _get_spec(self._con, ent_type)

        cur = self._con.cursor()
        cur.execute(ent_spec.drop_ndx, (ndx,))
        self._con.commit()

    def find_all(self, ent_type):
        ent_spec = _get_spec(self._con, ent_type)

        cur = self._con.cursor()
        cur.execute(ent_spec.find_all)
        return [ent_type._make(row) for row in cur.fetchall()]

    def find_by_ndx(self, ent_type, ndx):
        ent_spec = _get_spec(self._con, ent_type)

        cur = self._con.cursor()
        cur.execute(ent_spec.find_ndx, (ndx,))
        row = cur.fetchone()
        if row:
            return ent_type._make(row)
        
        return None

    def count(self, ent_type):
        ent_spec = _get_spec(self._con, ent_type)

        cur = self._con.cursor()
        cur.execute(ent_spec.count)
        ent_count, = cur.fetchone()
        return ent_count

    def backup(self, dst):
        self._con.backup(dst._con)

    def save_db(self, filename):
        dst = Db.to_file(filename)
        self.backup(dst)
        dst.close()

    def close(self):
        self._con.close()
