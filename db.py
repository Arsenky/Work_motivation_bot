import sqlite3
from loguru import logger


class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()

    def create_table(self):
        with self.connection:
            res = self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS users
            (id integer PRIMARY KEY AUTOINCREMENT,
            chat_id BIGINT,
            name text, 
            email TEXT,
            mob_tel BIGINT,
            result_inst INT,
            result_pro INT,
            result_ptr INT,
            result_hoz INT,
            result_lmp INT
            )
            ''')
            return res

    def log(func):
        def wrapper(self, *args, **kwargs):
            try:
                with self.connection:
                    res = func(self, *args, **kwargs)
                return res
            except Exception as ex:
                logger.error(f"{func} {ex}")
                return
        return wrapper

    @log
    def post_test_result(self, *args):
        l = (args)
        keys = "(chat_id, name, email, mob_tel, result_inst, result_pro, result_ptr, result_hoz, result_lmp)"
        print(l)
        try:
            with self.connection:
                self.cursor.execute(f"INSERT INTO users {keys} VALUES {l}")
        except:
            print("db error")
            