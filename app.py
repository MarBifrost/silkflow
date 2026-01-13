from flask import Flask, render_template
from flask_mysqldb import MySQL
from auth import auth_bp # Import the blueprint

app = Flask(__name__)
app.secret_key = 'mariam123'

# MySQL Configurations
app.config['MYSQL_HOST'] = '10.240.0.39'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'qwe123'
app.config['MYSQL_DB'] = 'silkflow_users'

mysql = MySQL(app)

# Register the Blueprint
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    # You can add logic here to check if user is logged in
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)