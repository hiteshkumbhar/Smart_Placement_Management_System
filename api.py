from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from models import db, Users, Students, Companies, Job_Drives, Applications, Interview_Rounds, Application_status
from zoneinfo import ZoneInfo
from auth import get_current_user
from utils.notifications import notifications
import os
from werkzeug.utils import secure_filename




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

@api_bp.get("/student/dashboard")
@jwt_required()
def student_dashboard():
    user = current_user()

    if not user:
        return error("User not found", 401)

    if user.role != "student":
        return error("Forbidden: students only", 403)

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return error("Student profile not found", 404)

    student_fields = [
        "branch", "cgpa", "skills", "resume_path", "graduation_year",
        "profile_pic", "mobile_number", "Gender", "DOB", "Address",
        "City", "State", "pin_code", "University_Roll_Number",
        "Semester", "tenth_Percentage", "Total_Backlogs",
        "Active_Backlogs", "LinkedIn", "GitHub", "Portfolio_Website",
        "LeetCode", "HackerRank", "Certification"
    ]

    student_optional_fields = [
        "twelth_Percentage", "Diploma_Percentage"
    ]

    filled_fields = 0
    total_fields = len(student_fields) + 1

    for field in student_fields:
        value = getattr(student, field, None)

        if value is not None and str(value).strip() != "":
            filled_fields += 1

    for field in student_optional_fields:
        value = getattr(student, field, None)

        if value is not None and str(value).strip() != "":
            filled_fields += 1
            break

    percentage = round((filled_fields / total_fields) * 100)

    resume_status = student.resume_status

    total_applications = (
        Applications.query
        .join(Job_Drives)
        .filter(
            Applications.student_id == student.id,
            Applications.status.notin_([
                Application_status.REJECTED,
                Application_status.SELECTED
            ]),
            Job_Drives.status != "Closed"
        )
        .count()
    )

    current_ist_time = (
        datetime.now(ZoneInfo("Asia/Kolkata"))
        .replace(tzinfo=None)
    )

    upcoming_interview_count = (
        db.session.query(Interview_Rounds)
        .join(
            Applications,
            Interview_Rounds.application_id == Applications.id
        )
        .filter(
            Applications.student_id == student.id,
            Interview_Rounds.result.is_(None),
            Interview_Rounds.date > current_ist_time
        )
        .count()
    )

    selections = (
        Applications.query
        .filter(
            Applications.student_id == student.id,
            Applications.status == Application_status.SELECTED
        )
        .count()
    )

    application_ids = db.session.scalars(
        db.select(Applications.id).where(
            Applications.student_id == student.id
        )
    ).all()

    rounds = (
        Interview_Rounds.query
        .filter(
            Interview_Rounds.application_id.in_(application_ids),
            Interview_Rounds.result.is_(None),
            Interview_Rounds.date > current_ist_time
        )
        .order_by(Interview_Rounds.date.asc())
        .limit(3)
        .all()
    )

    upcoming_interviews = []

    for interview in rounds:
        application_record = interview.Application
        job = application_record.Job_Drive

        upcoming_interviews.append({
            "company": (
                job.company.company_name if job.company else None
            ),
            "job_title": job.title,
            "round_name": interview.round_name,
            "date": (
                interview.date.isoformat()
                if interview.date else None
            ),
            "link": interview.link
        })

    recent_application_records = (
        Applications.query
        .join(Job_Drives)
        .filter(
            Applications.student_id == student.id,
            Job_Drives.status != "Closed"
        )
        .order_by(Applications.applied_at.desc())
        .limit(3)
        .all()
    )

    applications = []

    for application_record in recent_application_records:
        job = application_record.Job_Drive

        applications.append({
            "company": (
                job.company.company_name if job.company else None
            ),
            "job_title": job.title,
            "status": application_record.status.value
        })

    eligible_jobs = []

    if student.job_drive:
        eligible_drive_ids = []

        for value in student.job_drive.split(","):
            value = value.strip()
            eligible_drive_ids.append(int(value))

        if eligible_drive_ids:
            eligible_jobs = (
                Job_Drives.query
                .filter(
                    Job_Drives.id.in_(eligible_drive_ids),
                    Job_Drives.status == "Active"
                )
                .limit(3)
                .all()
            )

    jobs = []

    for job in eligible_jobs:
        jobs.append({
            "company": (
                job.company.company_name if job.company else None
            ),
            "title": job.title,
            "package": job.package,
            "location": job.location,
            "deadline": (
                job.deadline.isoformat()
                if job.deadline else None
            )
        })

    return jsonify({
        "profile_percentage": percentage,
        "resume_status": resume_status,
        "total_applications": total_applications,
        "upcoming_interview_count": upcoming_interview_count,
        "selections": selections,
        "upcoming_interviews": upcoming_interviews,
        "applications": applications,
        "eligible_jobs": jobs
    }), 200

@api_bp.get("/student/applications")
@jwt_required()
def student_applications():
    user = current_user()
    if not user:
        return error("User not found", 401)
    if user.role != "student":
        return error("Forbidden: students only", 403)
    student = Students.query.filter_by(user_id=user.user_id).first()
    if not student:
        return error("Student profile not found", 404)

    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("filter", "All").lower()
    search = request.args.get("search", "").strip()

    if page < 1:
        return error("Page must be greater than or equal to 1", 400)

    if status_filter == "inteview":
        status_filter = "interview"

    base_query = (
        Applications.query
        .join(Job_Drives)
        .filter(
            Applications.student_id == student.id,
            Job_Drives.status != "Closed"
        )
    )

    total_applications = base_query.count()

    shortlisted_count = base_query.filter(Applications.status == Application_status.SHORTLISTED).count()

    interview_count = base_query.filter(Applications.status == Application_status.INTERVIEW).count()

    select_count = base_query.filter(Applications.status == Application_status.SELECTED).count()

    reject_count = base_query.filter(Applications.status == Application_status.REJECTED).count()

    status_map = {
        "shortlisted": Application_status.SHORTLISTED,
        "interview": Application_status.INTERVIEW,
        "selected": Application_status.SELECTED,
        "rejected": Application_status.REJECTED,
    }

    if status_filter != "all":
        selected_status = status_map.get(status_filter)

        if selected_status is None:
            return error(
                "Invalid filter. Use All, shortlisted, interview, "
                "selected, or rejected.",
                400
            )

        base_query = base_query.filter(
            Applications.status == selected_status
        )

    if search:
        base_query = (base_query.join(Companies, Job_Drives.company_id == Companies.id).filter(Companies.company_name.ilike(f"%{search}%")))

    pagination = (base_query.order_by(Applications.applied_at.desc()).paginate(page=page,per_page=5,error_out=False))

    applications = []

    for application in pagination.items:
        job = application.Job_Drive
        company = job.company

        applications.append({
            "company": company.company_name if company else None,
            "job_title": job.title,
            "applied_at": (
                application.applied_at.isoformat()
                if application.applied_at else None
            ),
            "status": application.status.value,
            "drive_id": application.drive_id,
            "company_logo": company.logo_path if company else None
        })

    return jsonify({
        "student": {
            "user_id": student.user_id,
            "student_id": student.id
        },
        "counts": {
            "total_applications": total_applications,
            "shortlisted": shortlisted_count,
            "interview": interview_count,
            "selected": select_count,
            "rejected": reject_count
        },
        "applications": applications,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    }), 200

@api_bp.route("/student/application-details", methods=["GET"])
@jwt_required()
def student_application_details():
    user = current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    job_id = request.args.get("job_id", type=int)

    if not job_id:
        return jsonify({"error": "job_id is required"}), 400

    job_drive = Job_Drives.query.filter_by(id=job_id).first()

    if not job_drive:
        return jsonify({"error": "Job drive not found"}), 404

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    application = Applications.query.filter_by(drive_id=job_id,student_id=student.id).first()

    if not application:
        return jsonify({
            "error": "Application not found for this student and job"
        }), 404

    interview_rounds = application.Interview_Round

    response = {
        "job": {
            "id": job_drive.id,
            "title": job_drive.title,
            "company_name": job_drive.company.company_name
        },
        "application": {
            "id": application.id,
            "drive_id": application.drive_id,
            "student_id": application.student_id,
            "status": (
                application.status.value
                if application.status is not None
                and hasattr(application.status, "value")
                else application.status
            )
        },
        "interview_rounds": []
    }

    for round_data in interview_rounds:
        response["interview_rounds"].append({
            "round_name": round_data.round_name,
            "date": (
                round_data.date.isoformat()
                if round_data.date else None
            ),
            "result": round_data.result
        })

    return jsonify(response), 200


@api_bp.route("/student/interviews", methods=["GET"])
@jwt_required()
def student_interviews():

    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    today_start = datetime.datetime.combine(datetime.date.today(),datetime.time.min)
    tomorrow_start = today_start + datetime.timedelta(days=1)

    PER_PAGE = 5

    def get_page(parameter):
        try:
            value = int(request.args.get(parameter, 1))
            return max(value, 1)
        except (ValueError, TypeError):
            return 1

    past_page = get_page("page")
    today_page = get_page("today_page")
    upcoming_page = get_page("upcoming_page")

    past_search = request.args.get("past_search", "").strip()
    today_search = request.args.get("today_search", "").strip()
    upcoming_search = request.args.get("upcoming_search", "").strip()

    base_query = (
        Interview_Rounds.query
        .join(
            Applications,
            Interview_Rounds.application_id == Applications.id
        )
        .join(
            Job_Drives,
            Applications.drive_id == Job_Drives.id
        )
        .join(
            Companies,
            Job_Drives.company_id == Companies.id
        )
        .filter(Applications.student_id == student.id)
    )

    past_query = base_query.filter(Interview_Rounds.date < today_start)

    today_query = base_query.filter(Interview_Rounds.date >= today_start,Interview_Rounds.date < tomorrow_start)

    upcoming_query = base_query.filter(Interview_Rounds.date >= tomorrow_start)

    if past_search:
        past_query = past_query.filter(Companies.company_name.ilike(f"%{past_search}%"))

    if today_search:
        today_query = today_query.filter(Companies.company_name.ilike(f"%{today_search}%"))

    if upcoming_search:
        upcoming_query = upcoming_query.filter(Companies.company_name.ilike(f"%{upcoming_search}%"))

    past_pagination = (past_query.order_by(Interview_Rounds.date.desc()).paginate(page=past_page,
            per_page=PER_PAGE,
            error_out=False
        )
    )

    today_pagination = (
        today_query
        .order_by(Interview_Rounds.date.asc())
        .paginate(
            page=today_page,
            per_page=PER_PAGE,
            error_out=False
        )
    )

    upcoming_pagination = (
        upcoming_query
        .order_by(Interview_Rounds.date.asc())
        .paginate(
            page=upcoming_page,
            per_page=PER_PAGE,
            error_out=False
        )
    )

    def serialize_interview(round_data):
        application = round_data.Application
        job_drive = application.Job_Drive
        company = job_drive.company

        result = round_data.result

        if hasattr(result, "value"):
            result = result.value

        return {
            "interview_id": round_data.id,
            "company_name": company.company_name,
            "job_title": job_drive.title,
            "round_name": round_data.round_name,
            "date": (
                round_data.date.isoformat()
                if round_data.date else None
            ),
            "link": round_data.link,
            "result": result,
            "feedback": round_data.feedback,
            "company_logo": company.logo_path
        }

    response = {
        "student": {
            "user_id": student.user_id,
            "student_id": student.id
        },

        "past_interviews": {
            "items": [
                serialize_interview(r)
                for r in past_pagination.items
            ],
            "pagination": {
                "page": past_pagination.page,
                "per_page": past_pagination.per_page,
                "total_items": past_pagination.total,
                "total_pages": past_pagination.pages,
                "has_next": past_pagination.has_next,
                "has_prev": past_pagination.has_prev
            }
        },

        "todays_interviews": {
            "items": [
                serialize_interview(r)
                for r in today_pagination.items
            ],
            "pagination": {
                "page": today_pagination.page,
                "per_page": today_pagination.per_page,
                "total_items": today_pagination.total,
                "total_pages": today_pagination.pages,
                "has_next": today_pagination.has_next,
                "has_prev": today_pagination.has_prev
            }
        },

        "upcoming_interviews": {
            "items": [
                serialize_interview(r)
                for r in upcoming_pagination.items
            ],
            "pagination": {
                "page": upcoming_pagination.page,
                "per_page": upcoming_pagination.per_page,
                "total_items": upcoming_pagination.total,
                "total_pages": upcoming_pagination.pages,
                "has_next": upcoming_pagination.has_next,
                "has_prev": upcoming_pagination.has_prev
            }
        }
    }

    return jsonify(response), 200



def serialize_job_drive(job):
    return {
        "id": job.id,
        "company_name": job.company.company_name,
        "title": job.title,
        "package": job.package,
        "location": job.location,
        "deadline": job.deadline.isoformat() if job.deadline else None,
        "description": job.description,
        "status": job.status,
        "company_logo": job.company.logo_path
    }


def get_eligible_drive_ids(student):
    if not student.job_drive:
        return []

    eligible_ids = []

    for value in student.job_drive.split(","):
        value = value.strip()
        eligible_ids.append(int(value))

    return eligible_ids


@api_bp.route("/student/job-drives", methods=["GET"])
@jwt_required()
def student_job_drives():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    today = datetime.date.today()

    job_drives = Job_Drives.query.filter(Job_Drives.status != "Closed").all()
    for job in job_drives:
        if job.deadline and job.deadline.date() < today:
            job.status = "Expired"
        else:
            job.status = "Active"

    db.session.commit()

    eligible_ids = get_eligible_drive_ids(student)

    status_filter = request.args.get("filter", "Active").strip()
    search = request.args.get("search", "").strip()

    if status_filter not in ("Active", "Expired"):
        return jsonify({
            "error": "Invalid filter. Use Active or Expired."
        }), 400

    if eligible_ids:
        query = (
            Job_Drives.query
            .join(Companies)
            .filter(
                Job_Drives.id.in_(eligible_ids),
                Job_Drives.status == status_filter
            )
        )

        if search:
            query = query.filter(
                or_(
                    Companies.company_name.ilike(f"%{search}%"),
                    Job_Drives.title.ilike(f"%{search}%")
                )
            )

        jobs = query.order_by(Job_Drives.deadline.asc()).all()

    else:
        jobs = []

    return jsonify({
        "filter": status_filter,
        "search": search,
        "total": len(jobs),
        "jobs": [
            serialize_job_drive(job)
            for job in jobs
        ]
    }), 200

@api_bp.route("/student/job-drives/<int:job_id>/action",methods=["POST"])
@jwt_required()
def student_job_drive_action(job_id):

    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    data = request.get_json(silent=True) or {}

    action = data.get("action")

    if action not in ("apply", "opt_out"):
        return jsonify({"error": "Invalid action. Use 'apply' or 'opt_out'."}), 400

    job = Job_Drives.query.filter_by(id=job_id).first()

    if not job:
        return jsonify({"error": "Job drive not found"}), 404

    eligible_ids = get_eligible_drive_ids(student)

    if job_id not in eligible_ids:
        return jsonify({"error": "You are not eligible for this job drive."}), 403

    today = datetime.date.today()

    if job.status == "Closed":
        return jsonify({"error": "This job drive is closed."}), 400

    if job.deadline and job.deadline.date() < today:
        job.status = "Expired"
        db.session.commit()

        return jsonify({"error": "The application deadline has passed."}), 400

    job.status = "Active"

    if action == "apply":
        if student.resume_status != "Verified":
            return jsonify({"error": "Please wait until your resume is verified."}), 400

        existing_application = Applications.query.filter_by(student_id=student.id,drive_id=job_id).first()

        if existing_application:
            return jsonify({
                "error": "You have already applied for this job."
            }), 409

        # Create the application
        application = Applications(
            student_id=student.id,
            drive_id=job_id,
            status="APPLIED"
        )

        db.session.add(application)

        # Remove this job from the student's eligible-drive list
        eligible_ids.remove(job_id)

        student.job_drive = (
            ",".join(str(drive_id) for drive_id in eligible_ids)
            if eligible_ids else None
        )

        # Update the JSON notification counter
        app_count = dict(job.application_count_email or {})
        app_count["email_count"] = app_count.get("email_count", 0)
        app_count["student_id"] = list(
            app_count.get("student_id", [])
        )

        app_count["email_count"] += 1
        app_count["student_id"].append(student.id)

        # Preserve the original recruiter notification behavior
        if app_count["email_count"] >= 5:

            recruiter = Users.query.filter_by(
                user_id=job.creater_id
            ).first()

            student_list = []

            for student_id in app_count["student_id"]:
                applied_student = Students.query.filter_by(
                    id=student_id
                ).first()

                if applied_student:
                    student_list.append([
                        applied_student.user.name,
                        applied_student.branch,
                        applied_student.cgpa
                    ])

            if recruiter:
                notifications([
                    "Student_applied_Recruiter",
                    recruiter.email,
                    student_list,
                    job.title,
                    job.company.company_name
                ])

            app_count["email_count"] = 0
            app_count["student_id"] = []

        job.application_count_email = app_count

        db.session.commit()

        placement_officer_emails = [
            placement_officer.email
            for placement_officer in Users.query.filter_by(
                role="Placement_Officer"
            ).all()
        ]

        notifications([
            "Student_applied_Placement_officer",
            placement_officer_emails,
            student.user.name,
            job,
            job.company.company_name
        ])

        return jsonify({
            "message": "Application submitted successfully.",
            "application_id": application.id,
            "job_id": job.id,
            "status": "APPLIED"
        }), 201

    if action == "opt_out":

        existing_application = Applications.query.filter_by(student_id=student.id,drive_id=job_id).first()

        if existing_application:
            return jsonify({
                "error": "An application already exists for this job."
            }), 409

        # Remove the job from the student's eligible list
        eligible_ids.remove(job_id)

        student.job_drive = (
            ",".join(str(drive_id) for drive_id in eligible_ids)
            if eligible_ids else None
        )

        # Record the student opting out
        if job.opt_out is None:
            job.opt_out = str(student.id)
        else:
            opted_out_ids = [
                value.strip()
                for value in job.opt_out.split(",")
            ]

            if str(student.id) not in opted_out_ids:
                opted_out_ids.append(str(student.id))

            job.opt_out = ",".join(opted_out_ids)

        db.session.commit()

        placement_officer_emails = [placement_officer.email for placement_officer in Users.query.filter_by(role="Placement_Officer").all()]

        notifications([
            "Student_opted_out_Placement_officer",
            placement_officer_emails,
            student.user.name,
            job,
            job.company.company_name
        ])

        return jsonify({
            "message": "You have opted out of this job drive.",
            "job_id": job.id
        }), 200


@api_bp.route("/student/profile", methods=["GET", "POST", "PATCH"])
@jwt_required()
def student_profile_api():

    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    # ---------------- GET: View profile or download resume ----------------
    if request.method == "GET":

        if request.args.get("Download") == "download_resume":

            if not student.resume_path:
                return jsonify({"error": "No resume uploaded"}), 404

            resume_folder = os.path.join(
                current_app.root_path,
                "static", "Docs", "student", "resumes"
            )

            filename = secure_filename(student.resume_path)
            filepath = os.path.join(resume_folder, filename)

            if not os.path.isfile(filepath):
                return jsonify({"error": "Resume file not found"}), 404

            return send_from_directory(
                directory=resume_folder,
                path=filename,
                as_attachment=True,
                download_name=filename
            )

        return jsonify({
            "profile": {
                "user_id": user.user_id,
                "name": user.name,
                "branch": student.branch,
                "cgpa": student.cgpa,
                "skills": student.skills,
                "graduation_year": student.graduation_year,
                "mobile_number": student.mobile_number,
                "Gender": student.Gender,
                "DOB": student.DOB.isoformat() if student.DOB else None,
                "Address": student.Address,
                "City": student.City,
                "State": student.State,
                "pin_code": student.pin_code,
                "University_Roll_Number": student.University_Roll_Number,
                "Semester": student.Semester,
                "tenth_Percentage": student.tenth_Percentage,
                "twelth_Percentage": student.twelth_Percentage,
                "Diploma_Percentage": student.Diploma_Percentage,
                "Total_Backlogs": student.Total_Backlogs,
                "Active_Backlogs": student.Active_Backlogs,
                "LinkedIn": student.LinkedIn,
                "GitHub": student.GitHub,
                "Portfolio_Website": student.Portfolio_Website,
                "LeetCode": student.LeetCode,
                "HackerRank": student.HackerRank,
                "Certification": student.Certification,
                "profile_pic": student.profile_pic,
                "resume_path": student.resume_path,
                "resume_status": student.resume_status,
                "updated_at": (
                    student.updated_at.isoformat()
                    if student.updated_at else None
                )
            }
        }), 200

    # ---------------- POST/PATCH: Update profile or upload files ----------------

    action = request.args.get("action", "update")

    MAX_FILE_SIZE = 5 * 1024 * 1024

    # Upload profile photo
    if action == "change_photo":

        photo = request.files.get("profile_photo")

        if not photo or not photo.filename:
            return jsonify({"error": "Profile photo is required"}), 400

        photo.seek(0, os.SEEK_END)
        file_size = photo.tell()
        photo.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": "Photo must not exceed 5 MB"}), 413

        original_name = secure_filename(photo.filename)

        if "." not in original_name:
            return jsonify({"error": "Only JPG, JPEG, and PNG files are allowed"}), 400

        extension = original_name.rsplit(".", 1)[1].lower()

        if extension not in ("jpg", "jpeg", "png"):
            return jsonify({"error": "Only JPG, JPEG, and PNG files are allowed"}), 400

        folder = os.path.join(
            current_app.root_path,
            "static", "Images", "student", "profile_photo"
        )
        os.makedirs(folder, exist_ok=True)

        safe_name = secure_filename(user.name or "student")
        filename = f"User_{user.user_id}_{safe_name}.{extension}"

        try:
            photo.save(os.path.join(folder, filename))
            student.profile_pic = filename
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Profile photo upload failed")
            return jsonify({"error": "Unable to save profile photo"}), 500

        return jsonify({
            "message": "Profile photo updated successfully",
            "profile_pic": filename
        }), 200

    # Upload resume
    if action == "upload_resume":

        resume = request.files.get("resume_file")

        if not resume or not resume.filename:
            return jsonify({"error": "Resume file is required"}), 400

        resume.seek(0, os.SEEK_END)
        file_size = resume.tell()
        resume.seek(0)

        if file_size >= MAX_FILE_SIZE:
            return jsonify({"error": "Resume must be smaller than 5 MB"}), 413

        original_name = secure_filename(resume.filename)

        if "." not in original_name or original_name.rsplit(".", 1)[1].lower() != "pdf":
            return jsonify({"error": "Resume must be a PDF"}), 400

        folder = os.path.join(
            current_app.root_path,
            "static", "Docs", "student", "resumes"
        )
        os.makedirs(folder, exist_ok=True)

        safe_name = secure_filename(user.name or "student")
        filename = f"Resume_{user.user_id}_{safe_name}.pdf"
        is_reupload = bool(student.resume_path)

        try:
            resume.save(os.path.join(folder, filename))
            student.resume_path = filename

            if is_reupload:
                student.resume_status = "Reuploaded"

            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Resume upload failed")
            return jsonify({"error": "Unable to save resume"}), 500

        if is_reupload:
            try:
                officer_emails = [
                    officer.email
                    for officer in Users.query.filter_by(
                        role="Placement_Officer"
                    ).all()
                ]
                notifications([
                    "Student_resume_reuploaded",
                    officer_emails,
                    student.user.name
                ])
            except Exception:
                current_app.logger.exception("Resume notification failed")

        return jsonify({
            "message": "Resume uploaded successfully",
            "resume_path": student.resume_path,
            "resume_status": student.resume_status
        }), 200

    # Upload certification
    if action == "upload_certification":

        certification = request.files.get("Certification")

        if not certification or not certification.filename:
            return jsonify({"error": "Certification PDF is required"}), 400

        certification.seek(0, os.SEEK_END)
        file_size = certification.tell()
        certification.seek(0)

        if file_size >= MAX_FILE_SIZE:
            return jsonify({"error": "Certification must be smaller than 5 MB"}), 413

        original_name = secure_filename(certification.filename)

        if "." not in original_name or original_name.rsplit(".", 1)[1].lower() != "pdf":
            return jsonify({"error": "Certification must be a PDF"}), 400

        folder = os.path.join(
            current_app.root_path,
            "static", "Docs", "student", "certifications"
        )
        os.makedirs(folder, exist_ok=True)

        safe_name = secure_filename(user.name or "student")
        filename = f"Cert_{user.user_id}_{safe_name}_{original_name}"

        try:
            certification.save(os.path.join(folder, filename))

            existing = (student.Certification or "").strip()
            existing_names = [
                name.strip() for name in existing.split(",") if name.strip()
            ]

            if filename not in existing_names:
                existing_names.append(filename)

            student.Certification = ", ".join(existing_names)
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Certification upload failed")
            return jsonify({"error": "Unable to save certification"}), 500

        return jsonify({
            "message": "Certification uploaded successfully",
            "certifications": existing_names
        }), 201

    # Update profile fields using JSON
    if request.method in ("POST", "PATCH"):

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Send profile updates as a JSON object"
            }), 400

        allowed_fields = [
            "branch", "cgpa", "skills", "graduation_year",
            "mobile_number", "Gender", "DOB", "Address",
            "City", "State", "pin_code", "University_Roll_Number",
            "Semester", "tenth_Percentage", "twelth_Percentage",
            "Diploma_Percentage", "Total_Backlogs", "Active_Backlogs",
            "LinkedIn", "GitHub", "Portfolio_Website",
            "LeetCode", "HackerRank"
        ]

        unique_fields = [
            "mobile_number", "University_Roll_Number",
            "LinkedIn", "GitHub", "Portfolio_Website",
            "LeetCode", "HackerRank"
        ]

        for field in unique_fields:
            if field not in data or data[field] is None:
                continue

            value = data[field]

            if isinstance(value, str):
                value = value.strip()

            if not value:
                continue

            existing = db.session.query(
                getattr(Students, field)
            ).filter(
                getattr(Students, field) == value,
                Students.user_id != user.user_id
            ).first()

            if existing:
                return jsonify({
                    "error": f"This {field} is already taken",
                    "field": field
                }), 409

        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                return jsonify({"error": "Name must not be empty"}), 400

            user.name = data["name"].strip()

        for field in allowed_fields:
            if field in data:
                value = data[field]

                if isinstance(value, str):
                    value = value.strip()

                if field == "DOB" and value:
                    try:
                        value = datetime.date.fromisoformat(value)
                    except (ValueError, TypeError):
                        return jsonify({
                            "error": "DOB must use YYYY-MM-DD format"
                        }), 400

                setattr(student, field, value)

        student.updated_at = datetime.datetime.now(
            ZoneInfo("Asia/Kolkata")
        )

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Profile update failed")
            return jsonify({"error": "Unable to update profile"}), 500

        return jsonify({
            "message": "Profile updated successfully"
        }), 200

    return jsonify({"error": "Unsupported action"}), 400

@api_bp.route("/student/certification/download", methods=["GET"])
@jwt_required()
def student_download_certifications_api():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "student":
        return jsonify({"error": "Forbidden: students only"}), 403

    name = request.args.get("name", "").strip()

    if not name:
        return jsonify({"error": "Certification name is required"}), 400

    student = Students.query.filter_by(user_id=user.user_id).first()

    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    certifications = [item.strip() for item in (student.Certification or "").split(",") if item.strip()]

    if name not in certifications:
        return jsonify({
            "error": "Certification not found in your profile"
        }), 404

    safe_user_name = secure_filename(user.name or "student")
    safe_certification_name = secure_filename(name)

    filename = f"Cert_{user.user_id}_{safe_user_name}_{safe_certification_name}"

    certification_folder = os.path.join(
        current_app.root_path,
        "static",
        "Docs",
        "student",
        "certifications"
    )

    if not os.path.isfile(
        os.path.join(certification_folder, filename)
    ):
        return jsonify({"error": "Certification file not found"}), 404

    return send_from_directory(
        directory=certification_folder,
        path=filename,
        as_attachment=True,
        download_name=name
    )


########################################### Recruiter #################################################
@api_bp.route("/recruiter/dashboard", methods=["GET"])
@jwt_required()
def recruiter_dashboard_api():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "Recruiter":
        return jsonify({"error": "Forbidden: recruiters only"}), 403

    job_drive_count = Job_Drives.query.filter(
        Job_Drives.creater_id == user.user_id,
        Job_Drives.status != "Closed"
    ).count()

    # Get the recruiter's non-closed job drive IDs
    job_drive_ids = [
        result[0]
        for result in db.session.query(Job_Drives.id).filter(
            Job_Drives.creater_id == user.user_id,
            Job_Drives.status != "Closed"
        ).all()
    ]

    total_applicants = Applications.query.filter(Applications.drive_id.in_(job_drive_ids)).count()
    shortlisted = Applications.query.filter(Applications.drive_id.in_(job_drive_ids),Applications.status == Application_status.SHORTLISTED).count()
    selected = Applications.query.filter(Applications.drive_id.in_(job_drive_ids),Applications.status == Application_status.SELECTED).count()
    job_drives = Job_Drives.query.filter(Job_Drives.creater_id == user.user_id,Job_Drives.status != "Closed").all()

    job_drive_info = []

    for job in job_drives:

        applied = Applications.query.filter(Applications.drive_id == job.id,Applications.status == Application_status.APPLIED).count()
        shortlisted_count = Applications.query.filter(Applications.drive_id == job.id,Applications.status == Application_status.SHORTLISTED).count()
        interview = Applications.query.filter(Applications.drive_id == job.id,Applications.status == Application_status.INTERVIEW).count()
        selected_count = Applications.query.filter(Applications.drive_id == job.id,Applications.status == Application_status.SELECTED).count()
        job_drive_info.append({
            "title": job.title,
            "vacancies": job.Vacancies,
            "applied": applied,
            "shortlisted": shortlisted_count,
            "interview": interview,
            "selected": selected_count
        })

    application_ids = [result[0] for result in db.session.query(Applications.id).filter(Applications.drive_id.in_(job_drive_ids)).all()]
    interview_rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(application_ids)).all()

    today_interviews = []
    today = datetime.date.today()

    for interview_round in interview_rounds:

        if (interview_round.date and interview_round.date.date() == today and len(today_interviews) < 5):
            application = interview_round.Application
            job = application.Job_Drive

            today_interviews.append({
                "company_name": job.company.company_name,
                "job_title": job.title,
                "student_name": application.student.user.name,
                "interview": {
                    "id": interview_round.id,
                    "round_name": interview_round.round_name,
                    "date": interview_round.date.isoformat(),
                    "link": interview_round.link,
                    "result": (
                        interview_round.result.value
                        if hasattr(interview_round.result, "value")
                        else interview_round.result
                    ),
                    "feedback": interview_round.feedback
                }
            })

    # Return dashboard information as JSON
    return jsonify({
        "job_drive_count": job_drive_count,
        "total_applicants": total_applicants,
        "shortlisted": shortlisted,
        "selected": selected,
        "job_drive_info": job_drive_info,
        "today_interviews": today_interviews
    }), 200


@api_bp.route("/recruiter/job-drives", methods=["GET"])
@jwt_required()
def recruiter_job_drives_api():

    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "Recruiter":
        return jsonify({"error": "Forbidden: recruiters only"}), 403

    job_drives = Job_Drives.query.filter(Job_Drives.status != "Closed").all()

    for job in job_drives:
        if job.deadline.date() < datetime.date.today():
            job.status = "Expired"
            db.session.commit()
        else:
            job.status = "Active"
            db.session.commit()

    search = request.args.get("search", "").strip()

    if request.args.get("filter") == "Expired":

        if search:
            job_drives_results = (
                Job_Drives.query
                .join(
                    Companies,
                    Job_Drives.company_id == Companies.id
                )
                .filter(
                    or_(
                        Companies.company_name.ilike(f"%{search}%"),
                        Job_Drives.title.ilike(f"%{search}%"),
                        Job_Drives.location.ilike(f"%{search}%")
                    ),
                    Job_Drives.status == "Expired",
                    Job_Drives.creater_id == user.user_id
                )
            )
        else:
            job_drives_results = Job_Drives.query.filter_by(
                status="Expired",
                creater_id=user.user_id
            )

        jobs = []

        for job in job_drives_results:
            company = Companies.query.filter_by(id=job.company_id).first()

            jobs.append({"company_name": company.company_name, "job_drive": {"id": job.id, "title": job.title,
                        "status": job.status,
                        "package": job.package,
                        "location": job.location,
                        "deadline": (
                            job.deadline.isoformat()
                            if job.deadline else None
                        ),
                        "description": job.description,
                        "vacancies": job.Vacancies
                    },
                    "company_logo": company.logo_path
                })

        return jsonify({
            "filter": "Expired",
            "search": search,
            "total": len(jobs),
            "jobs": jobs
        }), 200

    query = Job_Drives.query.filter(Job_Drives.status != "Closed")

    if search:
        query = (
            query
            .join(
                Companies,
                Job_Drives.company_id == Companies.id
            )
            .filter(
                or_(
                    Companies.company_name.ilike(f"%{search}%"),
                    Job_Drives.title.ilike(f"%{search}%"),
                    Job_Drives.location.ilike(f"%{search}%")
                ),
                Job_Drives.creater_id == user.user_id
            )
        )

        job_drives_results = query.order_by(
            Job_Drives.title
        ).all()

        jobs = []

        for job in job_drives_results:
            company = Companies.query.filter_by(id=job.company_id).first()

            jobs.append({
                    "company_name": company.company_name,
                    "job_drive": {
                        "id": job.id,
                        "title": job.title,
                        "status": job.status,
                        "package": job.package,
                        "location": job.location,
                        "deadline": (
                            job.deadline.isoformat()
                            if job.deadline else None
                        ),
                        "description": job.description,
                        "vacancies": job.Vacancies
                    },
                    "company_logo": company.logo_path
                })

        return jsonify({
            "filter": "All",
            "search": search,
            "total": len(jobs),
            "jobs": jobs
        }), 200

    job_drives_results = Job_Drives.query.filter_by(
        status="Active",
        creater_id=user.user_id
    ).all()

    jobs = []

    for job in job_drives_results:
        company = Companies.query.filter_by(
            id=job.company_id
        ).first()

        jobs.append({
                "company_name": company.company_name,
                "job_drive": {
                    "id": job.id,
                    "title": job.title,
                    "status": job.status,
                    "package": job.package,
                    "location": job.location,
                    "deadline": (
                        job.deadline.isoformat()
                        if job.deadline else None
                    ),
                    "description": job.description,
                    "vacancies": job.Vacancies
                },
                "company_logo": company.logo_path
            })

    return jsonify({
        "filter": "Active",
        "search": "",
        "total": len(jobs),
        "jobs": jobs
    }), 200



@api_bp.route("/recruiter/schedule-interview", methods=["GET", "POST"])
@jwt_required()
def schedule_interview_api():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "Recruiter":
        return jsonify({"error": "Forbidden: recruiters only"}), 403

    # GET: Receive parameters from the URL
    if request.method == "GET":
        student_id = request.args.get("student_id")
        drive_id = request.args.get("drive_id")
        application_id = request.args.get("application_id")

    else:
        data = request.get_json(silent=True) or {}

        student_id = data.get("student_id")
        drive_id = data.get("drive_id")
        application_id = data.get("application_id")

    if not student_id or not drive_id or not application_id:
        return jsonify({
            "error": "student_id, drive_id, and application_id are required"
        }), 400

    try:
        drive_id = int(drive_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid drive_id"}), 400

    recruiter_drive_ids = [
        row[0]
        for row in db.session.query(Job_Drives.id).filter(
            Job_Drives.creater_id == user.user_id
        ).all()
    ]

    application = Applications.query.filter(
        Applications.student_id == student_id,
        Applications.id == application_id,
        Applications.drive_id == drive_id
    ).first()

    if (
        drive_id not in recruiter_drive_ids
        and application is None
    ):
        return jsonify({
            "error": "Forbidden: you cannot schedule an interview for this application"
        }), 403

    return jsonify({
        "message": "Interview scheduling details retrieved successfully",
        "student_id": student_id,
        "drive_id": drive_id,
        "application_id": application_id
    }), 200


@api_bp.route("/recruiter/applications", methods=["GET", "POST"])
@jwt_required()
def recruiter_applications_api():
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role != "Recruiter":
        return jsonify({"error": "Forbidden: recruiters only"}), 403

    search = request.args.get("search", "").strip()

    # Retrieve the recruiter's job drives
    if search:
        job_drives = (
            Job_Drives.query
            .join(
                Companies,
                Job_Drives.company_id == Companies.id
            )
            .filter(
                Job_Drives.title.ilike(f"%{search}%"),
                Job_Drives.creater_id == user.user_id,
                Job_Drives.status != "Closed"
            )
        )
    else:
        job_drives = Job_Drives.query.filter(
            Job_Drives.creater_id == user.user_id,
            Job_Drives.status != "Closed"
        )

    jobs = []

    for job in job_drives:
        company = Companies.query.filter_by(id=job.company_id).first()
        jobs.append({
                "company_name": company.company_name,
                "company_logo": company.logo_path,
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "status": job.status,
                    "package": job.package,
                    "location": job.location,
                    "deadline": (
                        job.deadline.isoformat()
                        if job.deadline else None
                    ),
                    "description": job.description,
                    "vacancies": job.Vacancies
                }
            })

    if request.method == "GET":
        return jsonify({
            "jobs": jobs,
            "total": len(jobs)
        }), 200

    # POST: Read action details from JSON
    data = request.get_json(silent=True) or {}

    mode = request.args.get("mode")
    student_id = data.get("student_id")
    drive_id = data.get("drive_id")

    if not student_id or not drive_id:
        return jsonify({
            "error": "student_id and drive_id are required"
        }), 400

    job = Job_Drives.query.filter_by(id=drive_id,creater_id=user.user_id).first()

    if not job:
        return jsonify({
            "error": "Job drive not found or access denied"
        }), 404

    application = Applications.query.filter_by(
        student_id=student_id,
        drive_id=drive_id
    ).first()

    if not application:
        return jsonify({
            "error": "Application not found"
        }), 404

    student = Students.query.filter_by(
        id=student_id
    ).first()

    if not student:
        return jsonify({
            "error": "Student not found"
        }), 404

    # ---------------------------------------
    # Update application status
    # ---------------------------------------
    if mode == "update":

        result = data.get("result")

        if application.status.value == "Applied":

            application.status = "SHORTLISTED"

            notifications([
                "shortlisted",
                student.user.email,
                job.company.company_name,
                job.title
            ])

            notifications([
                "student_shortlisted_placement_officer",
                [
                    officer.email
                    for officer in Users.query.filter(
                        Users.role == "Placement_Officer"
                    ).all()
                ],
                student.user.name,
                job.company.company_name,
                job.title
            ])

        elif (
            application.status.value == "Interview Scheduled"
            and result == "Select"
        ):

            application.status = "SELECTED"

            notifications([
                "selected",
                student.user.email,
                job.company.company_name,
                job.title
            ])

            notifications([
                "student_selected_placement_officer",
                [
                    officer.email
                    for officer in Users.query.filter(
                        Users.role == "Placement_Officer"
                    ).all()
                ],
                student.user.name,
                job.company.company_name,
                job.title
            ])

        elif (
            application.status.value == "Interview Scheduled"
            and result == "Reject"
        ):

            application.status = "REJECTED"

            notifications([
                "rejected",
                student.user.email,
                job.company.company_name,
                job.title
            ])

            notifications([
                "student_rejected_placement_officer",
                [
                    officer.email
                    for officer in Users.query.filter(
                        Users.role == "Placement_Officer"
                    ).all()
                ],
                student.user.name,
                job.company.company_name,
                job.title
            ])

        db.session.commit()


    elif mode == "schedule_interview":

        round_name = data.get("Round_Name")
        interview_date = data.get("Interview_Date")
        link = data.get("link")

        if not round_name or not interview_date:
            return jsonify({
                "error": "Round_Name and Interview_Date are required"
            }), 400

        application_id = db.session.query(
            Applications.id
        ).filter(
            Applications.student_id == student_id,
            Applications.drive_id == drive_id
        ).scalar()

        interview = Interview_Rounds(
            application_id=application_id,
            round_name=round_name,
            date=interview_date,
            link=link
        )

        application.status = "INTERVIEW"
        db.session.add(interview)
        db.session.commit()

        notifications([
            "Schedule_interview",
            student.user.email,
            job.company.company_name,
            job.title,
            round_name,
            interview_date
        ])

        notifications([
            "student_interview_scheduled_placement_officer",
            [
                officer.email
                for officer in Users.query.filter(
                    Users.role == "Placement_Officer"
                ).all()
            ],
            student.user.name,
            job.company.company_name,
            job.title,
            round_name,
            interview_date
        ])

    else:
        return jsonify({
            "error": "Invalid mode. Use 'update' or 'schedule_interview'."
        }), 400


    applicants = []

    applications = Applications.query.filter_by(
        drive_id=drive_id
    ).all()

    for app in applications:

        applicant_student = Students.query.filter_by(
            id=app.student_id
        ).first()

        if not applicant_student:
            continue

        applicant_name = db.session.query(
            Users.name
        ).filter(
            Users.user_id == applicant_student.user_id
        ).scalar()

        # Preserve original eligibility logic
        if (
            applicant_student.branch in job.Eligible_Branches
            and str(applicant_student.graduation_year)
            in job.Graduation_Year
            and applicant_student.cgpa >= float(job.CGPA)
        ):
            eligibility = "Eligible"
        else:
            eligibility = "Not Eligible"

        status = app.status.value if hasattr(
            app.status, "value"
        ) else app.status

        applicants.append({
            "application_id": app.id,
            "student_id": applicant_student.id,
            "student_name": applicant_name,
            "branch": applicant_student.branch,
            "cgpa": applicant_student.cgpa,
            "graduation_year": applicant_student.graduation_year,
            "status": status,
            "eligibility": eligibility
        })

    return jsonify({
        "message": "Operation completed successfully",
        "job": {
            "id": job.id,
            "title": job.title,
            "company_name": job.company.company_name
        },
        "applicants": applicants,
        "total_applicants": len(applicants)
    }), 200


@api_bp.route("/recruiter/certification/download", methods=["GET", "POST"])
@jwt_required()
def download_certifications_api():

    # Check authorization
    user = get_current_user()

    if not user:
        return jsonify({"error": "User not found"}), 401

    if user.role not in ["Recruiter", "Placement_Officer"]:
        return jsonify({"error": "Forbidden"}), 403

    if request.method == "GET":
        name = request.args.get("name")
        user_id = request.args.get("id")

    else:
        name = request.form.get("name")
        user_id = request.form.get("id")

    if not name or not user_id:
        return jsonify({
            "error": "Both name and id are required"
        }), 400

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user ID"}), 400

    student_name = db.session.query(Users.name).filter(
        Users.user_id == user_id
    ).scalar()

    if not student_name:
        return jsonify({"error": "User not found"}), 404

    filename = (
        f"Cert_{user_id}_{student_name}_{name}"
    )

    certification_folder = os.path.join(
        current_app.root_path,
        "static",
        "Docs",
        "student",
        "certifications"
    )

    safe_filename = secure_filename(filename)

    filepath = os.path.join(
        certification_folder,
        safe_filename
    )

    if not os.path.isfile(filepath):
        return jsonify({"error": "Certification file not found"}), 404

    return send_from_directory(
        directory=certification_folder,
        path=safe_filename,
        as_attachment=True,
        download_name=name
    )

