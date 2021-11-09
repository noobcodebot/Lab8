from flask import Flask, request, render_template, url_for, redirect
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
import os.path
from flask_admin import Admin
from flask_login import LoginManager

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + os.path.join(basedir, 'app.sqlite')
db = SQLAlchemy(app)
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=True)
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
admin = Admin(app, name='teacher-view', template_mode='bootstrap3')
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return Users.get(user_id)


class Users(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    username = db.Column(db.String(25), nullable=False)
    password = db.Column(db.String(25), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self, username):
        return f'Welcome, {username}'

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return True


class Classes(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    class_name = db.Column(db.String(100), nullable=False)
    timeslot = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    enrolled = db.Column(db.Integer, nullable=False)
    teacher_id = db.relationship('Teachers', backref=db.backref('teacher', lazy=True))


class Students(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    name = db.Column(db.String(25), nullable=False)
    user_id = db.relationship('User', backref=db.backref('user', lazy=True))


class Enrollment(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    student_id = db.relationship('Students', backref=db.backref('student', lazy=True))
    class_id = db.relationship('Classes', backref=db.backref('class', lazy=True))
    grade = db.Column(db.String(10), nullable=False)


class Teachers(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    name = db.Column(db.String(25), nullable=False)
    user_id = db.relationship('User', backref=db.backref('user', lazy=True))


class AdminView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


db.create_all()
db.session.commit()


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)


