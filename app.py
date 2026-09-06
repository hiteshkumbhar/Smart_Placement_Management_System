
from flask import Flask, render_template, request, redirect, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, Users, Students
from flask_login import LoginManager, login_user
from flask_login import logout_user, login_required
import os
from dotenv import load_dotenv
import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask_mail import Mail, Message
from student import student_bp
from Placement_officer import officer_bp
from Recruiter import Recruiter_bp
from utils.notifications import notifications
import socket

import socket

try:
    print('testing new connection')
    ip = socket.gethostbyname("smtp.gmail.com")
    print("Gmail IPv4:", ip)

    sock = socket.create_connection((ip, 587), timeout=10)
    print("IPv4 SMTP connection successful")
    sock.close()

except Exception as e:
    print("IPv4 SMTP connection failed:", repr(e))

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(student_bp)
app.register_blueprint(officer_bp)
app.register_blueprint(Recruiter_bp)

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_view = 'home'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

with app.app_context():
    db.create_all()
################################################ Home ##################################################
@app.route('/')
def home():
    return render_template('Home.html')
############################################ Reset password ###############################################33
@app.route('/Reset_Password', methods = ['GET', 'POST'])
def Reset_Password():
    if request.method == 'POST':
        email = request.form.get('Email')
        user = Users.query.filter_by(email=email).first()
        if user:
            flash('Check your email to reset the password','reset_password')
            token = s.dumps(email, salt='email-reset-salt')
            link = url_for('reset_token', token=token, _external=True)
            msg = Message('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f'Your link is {link}\n\nIf you did not request this, ignore this email.'
            try:
                mail.send(msg)
                return redirect(url_for('Reset_Password'))
            except Exception as e:
                return str(e)
        else:
            flash('User does not exist', 'reset_password')
            return redirect(url_for('Reset_Password'))
    return render_template('password_reset.html')

@app.route('/reset_password/', methods=['GET', 'POST'])
def reset_token():
    token = request.args.get('token')
    try:
        email = s.loads(token, salt='email-reset-salt', max_age=3600)
    except SignatureExpired:
        return 'The token is expired!'
    except Exception as e:
        return f'{e}'

    # If it's a POST request, update the password in the database
    if request.method == 'POST':
        new_password = request.form.get('password')
        user = Users.query.filter_by(email=email).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()
        return redirect(url_for('home'))

    # If it's a GET request, show them the form to enter a new password
    return render_template('New_password.html',token=token)

############################################## Logout ###################################################
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

############################################## Login ######################################################

@app.route('/Student_login', methods=['GET', 'POST'])
def Student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        Password = request.form.get('pass')
        user = Users.query.filter_by(email=email, role = "student").first()
        if user is None:
            flash('User does not exist', 'incorrect')
            return redirect(url_for('Student_login'))
        if check_password_hash(user.password, Password):
            login_user(user)
            return redirect(url_for('student.Student_Dashboard'))
        else:
            flash('Wrong username or password','incorrect')
            return redirect(url_for('Student_login'))
    return render_template('Login.html')

@app.route('/Recruiter_login', methods=['GET', 'POST'])
def Recruiter_login():
    if request.method == 'POST':
        email = request.form.get('email')
        Password = request.form.get('pass')
        user = Users.query.filter_by(email=email, role = "Recruiter").first()
        if user is None:
            flash('User does not exist', 'incorrect')
            return redirect(url_for('Recruiter_login'))
        if check_password_hash(user.password, Password):
            login_user(user)
            return redirect(url_for('Recruiter.Recruiter_Dashboard'))
        else:
            flash('Wrong username or password','incorrect')
            return redirect(url_for('Recruiter_login'))
    return render_template('Recruiter_login.html')

@app.route('/Placement_Officer_login',  methods=['GET', 'POST'])
def Placement_Officer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        Password = request.form.get('pass')
        user = Users.query.filter_by(email=email, role = "Placement_Officer").first()
        if user is None:
            flash('User does not exist', 'incorrect')
            return redirect(url_for('Placement_Officer_login'))
        if check_password_hash(user.password, Password):
            login_user(user)
            return redirect(url_for('Placement_officer.Placement_officer_dashboard'))
        else:
            flash('Wrong username or password','incorrect')
            return redirect(url_for('Placement_Officer_login'))
    return render_template('Placement_officer_login.html')

############################################ Register ################################################

@app.route('/Register', methods=['GET', 'POST'])
def Register():
    if request.method == 'POST':
        Email = request.form['Email']
        User = Users.query.filter_by(email=Email).first()
        if User:
            flash("User already exists", "User_exist")
            return render_template('Register.html')
        Password = request.form['Password']
        Confirm_password = request.form['confirm_password']
        if Password != Confirm_password:
            flash("Passwords do not match","mismatched_passwords")
            return render_template('Register.html')
        if 20 < len(Password) or len(Password) < 6 or len(Confirm_password) > 20 or len(Confirm_password) < 6:
            flash("Passwords length must be between 6 to 20 characters.", "mismatched_passwords")
            return render_template('Register.html')
        Username = request.form['Name']
        Role = request.form['Role']
        hashed = generate_password_hash(Password)
        user = Users(name=Username, email=Email, password=hashed, role=Role)
        db.session.add(user)
        db.session.commit()

        if Role == 'student':
            user = Users.query.filter_by(email=Email).first()
            Registeration_no = f"REGN{str(datetime.datetime.now().year)}{str(user.user_id)}"
            student = Students (user_id=user.user_id, registration_no=Registeration_no, placement_status = 'Open to Placement', Certification = '')
            db.session.add(student)
            db.session.commit()

        flash("Registration successful!", "success")
        notifications(['Registration',Username,Email,Role])
        return redirect(url_for('home'))
    return render_template('Register.html')

if __name__ == '__main__':
    app.run(debug=True)


