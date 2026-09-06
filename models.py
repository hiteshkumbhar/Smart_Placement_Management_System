from email.policy import default

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
from flask_login import UserMixin
from zoneinfo import ZoneInfo

db = SQLAlchemy()

class Users(UserMixin, db.Model):

    __tablename__ = "Users"
    user_id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100),nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255),nullable=False)
    role = db.Column(db.String(100),nullable=False)
    created_at = db.Column(db.DateTime, default = datetime.now(ZoneInfo('Asia/Kolkata')))

    def __repr__(self):
        return f"{self.name}"

    def get_id(self):
        return str(self.user_id)

class Students(db.Model):

    __tablename__ = "Students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'), nullable=False, unique=True,)
    registration_no = db.Column(db.String(100))
    branch = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    skills = db.Column(db.Text)
    resume_path = db.Column(db.Text)
    resume_status = db.Column(db.String(10), default='Pending')
    resume_remark = db.Column(db.Text)
    graduation_year = db.Column(db.Integer)
    profile_pic = db.Column(db.String(100))
    placement_status = db.Column(db.String(100))
    mobile_number = db.Column(db.String(15), unique=True)
    Gender = db.Column(db.String(100))
    DOB = db.Column(db.Date)
    Address = db.Column(db.Text)
    City = db.Column(db.String(100))
    State = db.Column(db.String(100))
    pin_code = db.Column(db.Integer)
    University_Roll_Number = db.Column(db.String(100), unique=True)
    Semester = db.Column(db.Integer)
    tenth_Percentage = db.Column(db.Float)
    twelth_Percentage = db.Column(db.Float)
    Diploma_Percentage =  db.Column(db.Float)
    Total_Backlogs = db.Column(db.String(2))
    Active_Backlogs = db.Column(db.String(2))
    created_at = db.Column(db.DateTime, default = datetime.now(ZoneInfo('Asia/Kolkata')))
    updated_at = db.Column(db.DateTime)
    LinkedIn = db.Column(db.String(500), unique=True)
    GitHub = db.Column(db.String(500), unique=True)
    Portfolio_Website = db.Column(db.String(500), unique=True)
    LeetCode = db.Column(db.String(500), unique=True)
    HackerRank  = db.Column(db.String(500), unique=True)
    Certification = db.Column(db.Text)
    job_drive = db.Column(db.Text)

    user = db.relationship('Users', backref='student_profile')

    # One-to-many relationship:
    Application = db.relationship('Applications', backref='student', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.id}"

class Companies(db.Model):

    __tablename__ = "Companies"
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(100), nullable=False)
    hr_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True)
    logo_path = db.Column(db.String(1000))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default = datetime.now(ZoneInfo('Asia/Kolkata')))
    creater_id = db.Column(db.Integer,  db.ForeignKey('Users.user_id'), nullable=False)

    # One-to-many relationship:
    Job_Drives = db.relationship('Job_Drives', backref='company', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.company_name}"

class Job_Drives(db.Model):

    __tablename__ = "Job_Drives"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('Companies.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    package = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    CGPA = db.Column(db.String(100))
    Eligible_Branches = db.Column(db.String(255))
    Graduation_Year = db.Column(db.String(500))
    Vacancies = db.Column(db.String(100))
    deadline = db.Column(db.DateTime)
    description = db.Column(db.Text)
    opt_out = db.Column(db.Text)
    posted = db.Column(db.String(1), default = 'N')
    status = db.Column(db.String(10), default = 'Active')
    created_at = db.Column(db.DateTime, default = datetime.now(ZoneInfo('Asia/Kolkata')))
    creater_id = db.Column(db.Integer,  db.ForeignKey('Users.user_id'), nullable=False)
    application_count_email = db.Column(db.JSON)


    Applications = db.relationship('Applications', backref='Job_Drive', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.title}"

class Application_status(Enum):
    APPLIED = "Applied"
    SHORTLISTED = "Shortlisted"
    INTERVIEW = "Interview Scheduled"
    SELECTED = "Selected"
    REJECTED = "Rejected"

class Applications(db.Model):
    __tablename__ = "Applications"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('Students.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('Job_Drives.id'), nullable=False)
    status =  db.Column(db.Enum(Application_status), nullable=False, default= Application_status.APPLIED)
    applied_at = db.Column(db.DateTime, default=datetime.now(ZoneInfo('Asia/Kolkata')), nullable=False)

    # One-to-many relationship:
    Interview_Round = db.relationship('Interview_Rounds', backref='Application', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"{self.id}"

class Interview_Rounds(db.Model):
    __tablename__ = "Interview_Rounds"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('Applications.id'), nullable=False)
    round_name =  db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    link = db.Column(db.Text)
    feedback = db.Column(db.Text)
    result = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now(ZoneInfo('Asia/Kolkata')))


    def __repr__(self):
        return f"{self.round_name}"