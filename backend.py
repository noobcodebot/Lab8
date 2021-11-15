from flask import Flask, request, render_template, url_for, redirect, flash
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, ForeignKey
import os.path
from flask_admin import Admin, expose, AdminIndexView
from flask_login import LoginManager, UserMixin, current_user, login_user, login_required, logout_user
from flask_admin.contrib.sqla import ModelView

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + os.path.join(basedir, 'app.sqlite')

db = SQLAlchemy(app)
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], echo=True)

app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.secret_key = 'keep secret'  # placeholder


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)


# restrict admin page from being accessed by students
class AdminIndex(AdminIndexView):
    @expose('/')
    def index(self):
        if not is_teacher(current_user) and not current_user.is_authenticated:
            return redirect(url_for('login'))
        return super(AdminIndex, self).index()

    def is_accessible(self):
        return is_teacher(current_user)


class AdminMixin:
    def is_accessible(self):
        return current_user.is_authenticated and is_teacher(current_user)

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    username = db.Column(db.String(25), nullable=False)
    password = db.Column(db.String(25), nullable=False)

    def check_password(self, password):
        return self.password == password


class Classes(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    class_name = db.Column(db.String(100), nullable=False)
    timeslot = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    enrolled = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    students = db.relationship('Students', secondary='enrollment')


class Students(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(25), nullable=False)
    last_name = db.Column(db.String(25), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    classes = db.relationship('Classes', secondary='enrollment')


class Teachers(AdminMixin, db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(25), nullable=False)
    last_name = db.Column(db.String(25), nullable=False)
    user_id = db.Column(db.String(10), db.ForeignKey('users.id'), nullable=False)
    classes = db.relationship('Classes', backref=db.backref('classes', lazy=True))


# joint table for M:M relationships
class Enrollment(db.Model):
    class_id = db.Column('class_id', db.Integer, db.ForeignKey('classes.id'), primary_key=True)
    student_id = db.Column('student_id', db.Integer, db.ForeignKey('students.id'), primary_key=True)
    grade = db.Column('grade', db.String(4), nullable=False)


# The following view classes are views added to admin page
class UserView(AdminMixin, sqla.ModelView):
    column_exclude_list = ['Password', ]
    pass


class ClassView(AdminMixin, sqla.ModelView):
    pass


class StudentView(AdminMixin, sqla.ModelView):
    pass


# sets up admin page, index_view takes the view perms from AdminIndex()
admin = Admin(app, name='teacher-view', template_mode='bootstrap3', index_view=AdminIndex())


# adding views to flask-admin
admin.add_view(UserView(Users, db.session))
admin.add_view(ClassView(Classes, db.session))
admin.add_view(StudentView(Students, db.session))

db.create_all()
db.session.commit()


# return true if user is a Teacher
def is_teacher(user):
    teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
    if teacher:
        return True


def get_user_classes(user):
    names = []
    if is_teacher(user):
        teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
        for name in teacher.classes:
            names.append(name.class_name)
        return names
    else:
        student = Students.query.filter(Students.user_id == user.id).first()
        for name in student.classes:
            names.append(name.class_name)
        return names


def get_teachers(user):
    names = []
    student = Students.query.filter(Students.user_id == user.id).first()
    for entry in student.classes:
        teacher = Teachers.query.filter(Teachers.id == entry.teacher_id).first()
        names.append(teacher.first_name + " " + teacher.last_name)
    return names


def get_class_times(user):
    times = []
    if is_teacher(user):
        teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
        for classes in teacher.classes:
            times.append(classes.timeslot)
        return times
    else:
        student = Students.query.filter(Students.user_id == user.id).first()
        for classes in student.classes:
            times.append(classes.timeslot)
        return times


def get_enrolled_students(user):
    numbers = []
    if is_teacher(user):
        teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
        for classes in teacher.classes:
            numbers.append(classes.enrolled)
        return numbers
    else:
        student = Students.query.filter(Students.user_id == user.id).first()
        for classes in student.classes:
            numbers.append(classes.enrolled)
        return numbers


def get_class_capacity(user):
    numbers = []
    if is_teacher(user):
        teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
        for classes in teacher.classes:
            numbers.append(classes.size)
        return numbers
    else:
        student = Students.query.filter(Students.user_id == user.id).first()
        for classes in student.classes:
            numbers.append(classes.size)
        return numbers


def check_class_capacity(student_class):
    return student_class.enrolled == student_class.size


def add_class(student_id, class_id):
    db.session.add(Enrollment(student_id=student_id, class_id=class_id, grade = "100"))
    db.session.commit()


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['POST', 'GET'])
def login(error='Invalid username or password'):
    # base case, when page is loaded, check if there's a currently authenticated user
    if current_user.is_authenticated:

        # if the user is authenticated and a teacher, load the teacher page. Later to change to /admin
        if is_teacher(current_user):
            return redirect(url_for('teacher_page', user_id=current_user.id))

        # base return value for students
        return redirect(url_for('user_page', user_id=current_user.id))

    # when a form is submitted using POST, execute login logic
    if request.method == 'POST':
        user = Users.query.filter_by(username=request.form['username']).first()
        if user is None or not user.check_password(request.form['password']):
            return render_template('login.html', error=error)
        login_user(user)
        if is_teacher(user):
            return redirect(url_for('teacher_page', user_id=current_user.id))
        return redirect(url_for('user_page', user_id=current_user.id))
    return render_template('login.html')


# app route for a logged in user who isn't a teacher
@app.route('/user/classes', methods=['POST', 'GET'])
@login_required
def user_page():
    if request.method == 'POST':
        return redirect(url_for('registration'))
    else:
        user = Users.query.filter_by(id=current_user.id).first()
        student = Students.query.filter(Students.user_id == user.id).first()
        name = student.first_name
        classes = get_user_classes(user)
        teachers = get_teachers(user)
        times = get_class_times(user)
        enrolled = get_enrolled_students(user)
        cap = get_class_capacity(user)
        return render_template(
            'user_page.html', classes=classes, teachers=teachers, times=times, enrolled=enrolled, cap=cap, name=name
        )


@app.route('/teacher', methods=['POST', 'GET'])
def teacher_page():
    user = Users.query.filter_by(id=current_user.id).first()
    teacher = Teachers.query.filter(Teachers.user_id == user.id).first()
    name = "Dr. " + teacher.last_name
    classes = get_user_classes(user)
    teachers = []
    for entry in classes:
        c = Classes.query.filter(Classes.class_name == entry).first()
        teacher = Teachers.query.filter(c.teacher_id == Teachers.id).first()
        teachers.append(teacher.first_name + " " + teacher.last_name)
    times = get_class_times(user)
    enrolled = get_enrolled_students(user)
    cap = get_class_capacity(user)
    return render_template(
        'teacher_page.html', classes=classes, enrolled=enrolled, times=times, name=name, cap=cap, teachers=teachers
    )


@app.route('/user/registration', methods=['POST', 'GET'])
@login_required
def registration():
    if request.method == 'POST':
        classID = int(request.form['class'])
        selectedClass = Classes.query.filter(Classes.id == classID).first()
        if check_class_capacity(selectedClass):
            return render_template(
                'registration.html', class_names=class_names, times=times, enrolled=enrolled, cap=cap,
                name=name, classes=classes, teachers=Teachers)
        else:
            add_class(current_user.id,classID)
        return redirect(url_for('user_page'))
    user = Users.query.filter_by(id=current_user.id).first()
    student = Students.query.filter(Students.user_id == user.id).first()
    name = student.first_name
    classes = Classes.query.all()
    class_names = []
    times = []
    enrolled = []
    cap = []
    for c in classes:
        class_names.append(c.class_name)
        times.append(c.timeslot)
        enrolled.append(c.enrolled)
        cap.append(c.size)
    # full = check_class_capacity()
    return render_template(
        'registration.html', class_names=class_names, times=times, enrolled=enrolled, cap=cap,
        name=name, classes=classes, teachers=Teachers
    )


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/class/', methods=['GET', 'POST'])
@login_required
def class_cs106():
    if not is_teacher(current_user):
        flash('You do not have permission to view this page')
        return redirect(url_for('login'))
    return render_template('cse106.html')



if __name__ == '__main__':
    app.run(debug=True)
