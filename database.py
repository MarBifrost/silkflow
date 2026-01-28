# import MySQLdb
# from MySQLdb.cursors import DictCursor
#
#
# mysql = None
#
# def init_db(app):
#     global mysql
#
#     try:
#         mysql = MySQLdb.connect(
#             host=app.config['MYSQL_HOST'],
#             user=app.config['MYSQL_USER'],
#             passwd=app.config['MYSQL_PASSWORD'],
#             db=app.config['MYSQL_DB'],
#             cursorclass=DictCursor,
#             charset='utf8',
#             use_unicode=True,
#         )
#         print("Connected to MySQL!")
#     except MySQLdb.Error as e:
#         print("Failed to connect to Mysql: {}".format(e))
#         raise
#
# def get_db():
#     global mysql
#     if mysql is None:
#         raise RuntimeError("Database not initialized")
#     return mysql
#

# database.py
import MySQLdb
from MySQLdb.cursors import DictCursor

mysql = None

def init_db(app):
    global mysql
    print("[DEBUG] Starting init_db(app)")
    try:
        mysql = MySQLdb.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            passwd=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB'],
            cursorclass=DictCursor,
            charset='utf8mb4',
            use_unicode=True,
        )
        print("[DEBUG] MySQL connection SUCCESSFULLY created")
        print(f"[DEBUG] mysql object after connect: {mysql}")
    except MySQLdb.Error as e:
        print(f"[ERROR] Failed to connect to MySQL: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Unexpected error in init_db: {e}")
        raise

def get_db():
    global mysql
    print(f"[DEBUG] get_db() called, current mysql = {mysql}")
    if mysql is None:
        raise RuntimeError("Database not initialized. Call init_db(app) first.")
    return mysql