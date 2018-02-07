import sqlite3
from sqlite3 import Error


class SqlLite:

    def __init__(self, db_path):
        try:
            self.conn = sqlite3.connect(db_path)
        except Error as e:
            print(e)

    def execute(self, statement):
        cursor = self.conn.cursor()
        cursor.execute(statement)

    def execute_insert(self, statement, data):
        cursor = self.conn.cursor()

        try:
            cursor.executemany(statement, data)
            self.conn.commit()
        except Error as e:
            print("Failed to insert : ", data, e)

    def execute_select(self, statement):
        self.conn.row_factory = self.dict_factory
        cursor = self.conn.cursor()

        try:
            rows = cursor.execute(statement)
            return rows.fetchall()
        except Error as e:
            print("Failed to select : ", e)
            return []

    @staticmethod
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d
