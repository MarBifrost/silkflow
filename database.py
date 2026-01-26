import MySQLdb
from MySQLdb.cursors import DictCursor


mysql = None

def init_db(app):
    global mysql

    try:
        mysql = MySQLdb.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            passwd=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB'],
            cursorclass=DictCursor,
            charset='utf8',
            use_unicode=True,
        )
        print("Connected to MySQL!")
    except MySQLdb.Error as e:
        print("Failed to connect to Mysql: {}".format(e))
        raise

def get_db():
    global mysql
    if mysql is None:
        raise RuntimeError("Database not initialized")
    return mysql

