from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from models import db, Users, Students, Companies, Job_Drives, Applications, Interview_Rounds, Application_status

api_bp = Blueprint("api", __name__, url_prefix="/api")


def current_user():
    try:
        return Users.query.get(int(get_jwt_identity()))
    except (TypeError, ValueError):
        return None


def error(message, code):
    return jsonify({"error": message}), code


def student_json(s):
    return {
        "id": s.id, "user_id": s.user_id, "name": s.user.name if s.user else None,
        "email": s.user.email if s.user else None, "registration_no": s.registration_no,
        "branch": s.branch, "cgpa": s.cgpa, "skills": s.skills,
        "graduation_year": s.graduation_year, "resume_status": s.resume_status,
        "placement_status": s.placement_status, "mobile_number": s.mobile_number
    }


def job_json(j):
    return {
        "id": j.id, "company_id": j.company_id,
        "company": j.company.company_name if j.company else None,
        "title": j.title, "package": j.package, "location": j.location,
        "cgpa": j.CGPA, "eligible_branches": j.Eligible_Branches,
        "graduation_year": j.Graduation_Year, "vacancies": j.Vacancies,
        "deadline": j.deadline.isoformat() if j.deadline else None,
        "description": j.description, "status": j.status
    }


def application_json(a):
    return {
        "id": a.id, "student_id": a.student_id, "job_id": a.drive_id,
        "job_title": a.Job_Drive.title if a.Job_Drive else None,
        "company": a.Job_Drive.company.company_name if a.Job_Drive and a.Job_Drive.company else None,
        "status": a.status.value if a.status else None,
        "applied_at": a.applied_at.isoformat() if a.applied_at else None
    }


@api_bp.post("/login")
def api_login():
    data = request.get_json(silent=True) or {}
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        return error("email and password are required", 400)
    user = Users.query.filter_by(email=email).first()
    if not user:
        return error("User does not exist", 401)
    if not check_password_hash(user.password, password):
        return error("Invalid password", 401)
    token = create_access_token(identity=str(user.user_id))
    return jsonify({"access_token": token, "token_type": "Bearer", "user": {"id": user.user_id, "name": user.name, "email": user.email, "role": user.role}}), 200


@api_bp.get("/students")
@jwt_required()
def list_students():
    user = current_user()
    if not user:
        return error("User not found", 401)
    if user.role not in ("Placement_Officer"):
        return error("Forbidden", 403)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    query = Students.query.join(Users)
    search = request.args.get("search", "").strip()
    branch = request.args.get("branch")
    graduation_year = request.args.get("graduation_year", type=int)
    if search:
        query = query.filter(or_(Users.name.ilike(f"%{search}%"),
                                 Users.email.ilike(f"%{search}%"),
                                 Students.registration_no.ilike(f"%{search}%")))
    if branch:
        query = query.filter(Students.branch.ilike(f"%{branch}%"))
    if graduation_year:
        query = query.filter(Students.graduation_year == graduation_year)
    pagination = query.order_by(Students.id).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({"items": [student_json(s) for s in pagination.items],
                    "page": page, "per_page": per_page, "total": pagination.total,
                    "pages": pagination.pages})


@api_bp.route("/students/<int:student_id>", methods=["GET", "POST", "PUT", "DELETE"])
@jwt_required()
def student_detail(student_id):
    user = current_user()
    s = Students.query.get_or_404(student_id)
    own_profile = user and s.user_id == user.user_id
    staff = user and user.role in ("Placement_Officer")
    if not (own_profile or staff):
        return error("Forbidden", 403)
    if request.method == "GET":
        return jsonify(student_json(s))
    if request.method in ("POST", "PUT"):
        data = request.get_json(silent=True) or {}
        allowed = {"registration_no", "branch", "cgpa", "skills", "graduation_year",
                    "mobile_number", "placement_status"}
        for key in allowed:
            if key in data:
                setattr(s, key, data[key])
        db.session.commit()
        return jsonify(student_json(s)), 200
    if not staff:
        return error("Only placement staff can delete student profiles", 403)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"message": "Student deleted"}), 200


@api_bp.route("/jobs", methods=["GET", "POST"])
@jwt_required()
def jobs():
    user = current_user()
    if not user:
        return error("User not found", 401)
    if request.method == "GET":
        query = Job_Drives.query
        status = request.args.get("status", "Active")
        if status:
            query = query.filter_by(status=status)
        location = request.args.get("location")
        if location:
            query = query.filter(Job_Drives.location.ilike(f"%{location}%"))
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
        p = query.order_by(Job_Drives.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({"items": [job_json(j) for j in p.items], "page": page,
                        "per_page": per_page, "total": p.total, "pages": p.pages})
    if user.role not in ("Recruiter", "Placement_Officer"):
        return error("Forbidden", 403)
    data = request.get_json(silent=True) or {}
    required = ("title", "package", "location")
    if any(not data.get(k) for k in required):
        return error("title, package and location are required", 400)
    company_id = data.get("company_id")
    company = Companies.query.get(company_id) if company_id else Companies.query.filter_by(creater_id=user.user_id).first()
    if not company:
        return error("Create/select a company before posting a job", 400)
    if user.role in ("Recruiter", "Placement_Officer") and company.creater_id != user.user_id:
        return error("You can only post jobs for your company", 403)
    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(data["deadline"])
        except (ValueError, TypeError):
            return error("deadline must be an ISO-8601 date/time", 400)
    job = Job_Drives(company_id=company.id, title=data["title"],
        package=float(data["package"]), location=data["location"],
        CGPA=data.get("cgpa"), Eligible_Branches=data.get("eligible_branches"),
        Graduation_Year=data.get("graduation_year"), Vacancies=data.get("vacancies"),
        deadline=deadline, description=data.get("description"),
        status=data.get("status", "Active"), creater_id=user.user_id)
    db.session.add(job)
    db.session.commit()
    return jsonify(job_json(job)), 201


@api_bp.post("/applications")
@jwt_required()
def apply_for_job():
    user = current_user()
    if not user or user.role != "student":
        return error("Only student accounts can apply", 403)
    student = Students.query.filter_by(user_id=user.user_id).first()
    if not student:
        return error("Student profile not found", 404)
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id", data.get("drive_id"))
    if not job_id:
        return error("job_id is required", 400)
    job = Job_Drives.query.get(job_id)
    if not job or job.status != "Active":
        return error("Active job not found", 404)
    existing = Applications.query.filter_by(student_id=student.id, drive_id=job.id).first()
    if existing:
        return error("You have already applied for this job", 409)
    app = Applications(student_id=student.id, drive_id=job.id)
    db.session.add(app)
    db.session.commit()
    return jsonify(application_json(app)), 201


@api_bp.get("/applications/<int:application_id>")
@jwt_required()
def application_status(application_id):
    user = current_user()
    a = Applications.query.get_or_404(application_id)
    student = Students.query.filter_by(user_id=user.user_id).first() if user and user.role == "student" else None
    staff = user and user.role in ("Recruiter", "Placement_Officer")
    if not (staff or (student and a.student_id == student.id)):
        return error("Forbidden", 403)
    return jsonify(application_json(a))


@api_bp.put("/applications/<int:application_id>/status")
@jwt_required()
def update_application_status(application_id):
    user = current_user()
    if not user or user.role not in ("Recruiter"):
        return error("Forbidden", 403)
    a = Applications.query.get_or_404(application_id)
    data = request.get_json(silent=True) or {}
    raw_status = data.get("status")
    try:
        a.status = Application_status(raw_status)
    except (ValueError, TypeError):
        return error("status must be one of: " + ", ".join(s.value for s in Application_status), 400)
    db.session.commit()
    return jsonify(application_json(a))


@api_bp.post("/interviews")
@jwt_required()
def schedule_interview():
    user = current_user()
    if not user or user.role not in ("Recruiter"):
        return error("Forbidden", 403)
    data = request.get_json(silent=True) or {}
    if not data.get("application_id") or not data.get("round_name") or not data.get("date"):
        return error("application_id, round_name and date are required", 400)
    a = Applications.query.get(data["application_id"])
    if not a:
        return error("Application not found", 404)
    try:
        date = datetime.fromisoformat(data["date"])
    except (ValueError, TypeError):
        return error("date must be an ISO-8601 date/time", 400)
    interview = Interview_Rounds(application_id=a.id, round_name=data["round_name"],
                                 date=date, link=data.get("link"))
    a.status = Application_status.INTERVIEW
    db.session.add(interview)
    db.session.commit()
    return jsonify({"id": interview.id, "application_id": interview.application_id,
                    "round_name": interview.round_name, "date": interview.date.isoformat(),
                    "link": interview.link}), 201
