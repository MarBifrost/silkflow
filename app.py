from flask import Flask

app = Flask(__name__)


@app.route('/')
def index():  # put application's code here
    return '/template/index'


if __name__ == '__main__':
    app.run()
