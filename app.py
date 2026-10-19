
from flask import Flask, render_template, request, redirect, flash, url_for, g
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, Users, Students
from flask_jwt_extended import (create_access_token,create_refresh_token,set_access_cookies,set_refresh_cookies,unset_jwt_cookies, get_csrf_token,jwt_required, verify_jwt_in_request,get_jwt_identity,get_jwt, JWTManager)
from auth import init_jwt, get_current_user, jwt
import os
from dotenv import load_dotenv
import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from student import student_bp
from Placement_officer import officer_bp
from Recruiter import Recruiter_bp
from utils.notifications import notifications, send_email
from api import api_bp
load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config.from_object(Config)
db.init_app(app)

app.register_blueprint(student_bp)
app.register_blueprint(officer_bp)
app.register_blueprint(Recruiter_bp)
app.register_blueprint(api_bp)

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

init_jwt(app)

with app.app_context():
    db.create_all()

@app.errorhandler(400)
def handle_bad_request(error):
    return render_template('400.html'), 400

@app.errorhandler(401)
def handle_unauthorized(error):
    return render_template('401.html'), 401

@app.errorhandler(403)
def handle_forbidden(error):
    return render_template('403.html'), 403

@app.errorhandler(404)
def handle_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def handle_internal_server_error(error):
    return render_template('500.html'), 500
################################################ Home ##################################################
@app.route('/')
def home():
    return render_template('Home.html')
############################################ Reset password ###############################################33
@app.route('/Reset_Password', methods=['GET', 'POST'])
def Reset_Password():
    if request.method == 'POST':
        email = request.form.get('Email')
        user = Users.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email,salt='email-reset-salt')
            link = url_for('reset_token',token=token,_external=True)
            html_content = f"""
                <h2>Password Reset Request</h2>

                <p>
                    You requested to reset your password.
                </p>

                <p>
                    Click the link below to reset your password:
                </p>

                <p>
                    <a href="{link}">Reset Password</a>
                </p>

                <p>
                    This link will expire in 1 hour.
                </p>

                <p>
                    If you did not request this, please ignore this email.
                </p>
            """
            email_sent = send_email(email,'Password Reset Request',html_content)
            if email_sent:
                flash('Check your email to reset the password','reset_password')
            else:
                flash('Unable to send reset email. Please try again later.','reset_password')
            return redirect(url_for('Reset_Password'))
        else:
            flash('User does not exist','reset_password')
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
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = redirect(url_for('home'))
    unset_jwt_cookies(response)
    return response

############################################## Login ######################################################

@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():

    identity = get_jwt_identity()

    # Confirm that the account still exists.
    user = Users.query.filter_by(
        user_id=int(identity)
    ).first()

    if user is None:
        return jsonify({"error": "User no longer exists"}), 401

    new_access_token = create_access_token(
        identity=str(user.user_id)
    )

    response = jsonify({
        "message": "Access token refreshed"
    })

    set_access_cookies(response, new_access_token)

    return response

@app.before_request
def refresh_access_token_if_needed():
    # Skip authentication endpoints.
    if request.endpoint in (
        "home",
        "Student_login",
        "Recruiter_login",
        "Placement_Officer_login",
        "refresh_and_continue",
    ):
        return None

    # Only refresh when an access cookie exists.
    access_cookie_name = app.config["JWT_ACCESS_COOKIE_NAME"]
    encoded_token = request.cookies.get(access_cookie_name)

    if not encoded_token:
        return None

    try:
        # Validate the access token before using its claims.
        verify_jwt_in_request(optional=True)

        claims = get_jwt()
        expiration = claims.get("exp")

        if expiration is None:
            return None

        # Refresh when fewer than five minutes remain.
        if expiration - time.time() < 300:
            identity = get_jwt_identity()

            if identity is not None:
                g.new_access_token = create_access_token(
                    identity=identity
                )

    except Exception:
        # Let the normal JWT validation/error handling
        # handle missing, invalid, or expired tokens.
        return None

    return None

@app.after_request
def set_refreshed_access_token(response):
    new_token = getattr(g, "new_access_token", None)

    if new_token:
        set_access_cookies(response, new_token)

    return response

@app.route("/refresh-and-continue", methods=["GET"])
@jwt_required(refresh=True)
def refresh_and_continue():

    identity = get_jwt_identity()

    new_access_token = create_access_token(
        identity=identity
    )

    # Get the page the user originally requested.
    target = request.args.get("next", "/")

    # Only allow relative paths on this application.
    parsed_target = urlsplit(target)

    if (
        not target.startswith("/")
        or target.startswith("//")
        or parsed_target.scheme
        or parsed_target.netloc
    ):
        target = "/"

    response = redirect(target)

    set_access_cookies(response, new_access_token)

    return response

@jwt.expired_token_loader
def handle_expired_token(jwt_header, jwt_payload):

    # Automatically recover expired tokens during
    # normal page navigation.
    if request.method in ("GET", "HEAD"):
        return redirect(
            url_for(
                "refresh_and_continue",
                next=request.full_path.rstrip("?")
            )
        )

    # Do not silently discard a submitted form.
    return (
        "Your session expired. Please refresh the page "
        "and submit the form again.",
        401
    )

@jwt.unauthorized_loader
def custom_unauthorized_response(callback):
    # Renders an HTML page from your templates folder with a 401 Unauthorized status
    return render_template("401.html"), 401

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
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id))
            response = redirect(url_for('student.Student_Dashboard'))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
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
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id))
            response = redirect(url_for('Recruiter.Recruiter_Dashboard'))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
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
            access_token = create_access_token(identity=str(user.user_id))
            refresh_token = create_refresh_token(identity=str(user.user_id))
            response = redirect(url_for('Placement_officer.Placement_officer_dashboard'))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            return response
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

@app.context_processor
def inject_template_context():

    csrf_token = None
    current_user = None

    try:
        # Check whether a valid JWT is present.
        verify_jwt_in_request(optional=True)

        # Retrieve the authenticated user from the database.
        current_user = get_current_user()

        # Retrieve the CSRF token associated with the JWT cookie.
        if current_user is not None:
            encoded_token = request.cookies.get(
                app.config["JWT_ACCESS_COOKIE_NAME"]
            )

            if encoded_token:
                csrf_token = get_csrf_token(encoded_token)

    except Exception:
        current_user = None
        csrf_token = None

    return {
        "current_user": current_user,
        "csrf_token": csrf_token
    }

if __name__ == '__main__':
    app.run()


