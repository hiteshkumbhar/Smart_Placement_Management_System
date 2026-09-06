from flask import render_template, request, redirect, flash, url_for, abort, send_from_directory, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Users, Students, Companies, Job_Drives, Application_status, Applications, Interview_Rounds
import os
import datetime
from . import Recruiter_bp
from utils.notifications import notifications

@Recruiter_bp.route('/Recruiter_Dashboard')
@login_required
def Recruiter_Dashboard():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden

    job_drive_count = Job_Drives.query.filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed').count()
    total_applicants = Applications.query.filter(Applications.drive_id.in_([result[0] for result in db.session.query(Job_Drives.id).filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed').all()])).count()
    shortlisted = Applications.query.filter(Applications.drive_id.in_([result[0] for result in db.session.query(Job_Drives.id).filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed').all()]), Applications.status == Application_status.SHORTLISTED).count()
    selected = Applications.query.filter(Applications.drive_id.in_([result[0] for result in db.session.query(Job_Drives.id).filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed').all()]), Applications.status == Application_status.SELECTED).count()
    Job_drive = Job_Drives.query.filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed').all()

    Job_drive_info = []
    for job in Job_drive:
        Applied = Applications.query.filter(Applications.drive_id == job.id, Applications.status == Application_status.APPLIED).count()
        shortlisted = Applications.query.filter(Applications.drive_id == job.id, Applications.status == Application_status.SHORTLISTED).count()
        Interview = Applications.query.filter(Applications.drive_id == job.id, Applications.status == Application_status.INTERVIEW).count()
        selected = Applications.query.filter(Applications.drive_id == job.id, Applications.status == Application_status.SELECTED).count()
        Job_drive_info.append([job.title, job.Vacancies, Applied, shortlisted, Interview, selected])

    inner_query = [r[0] for r in db.session.query(Applications.id).filter(Applications.drive_id.in_([x.id for x in Job_drive])).all()]
    interview_rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(inner_query)).all()

    today_interview = []
    count = 0
    for round in interview_rounds:
        if round.date.date() == datetime.date.today() and count < 5:
            today_interview.append([round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title,round.Application.student.user.name, round])
            count += 1

    return render_template('Recruiter_Dashboard.html', job_drive_count = job_drive_count, total_applicants = total_applicants, shortlisted = shortlisted, selected = selected, Job_drive_info = Job_drive_info, today_interview = today_interview)


@Recruiter_bp.route('/Job_drive')
@login_required
def Job_drive():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden

    job_drives = Job_Drives.query.filter(Job_Drives.status != 'Closed').all()
    for job in job_drives:
        if job.deadline.date() < datetime.date.today():
            job.status = 'Expired'
            db.session.commit()
        else:
            job.status = 'Active'
            db.session.commit()

    if request.args.get('filter') == 'Expired':
        job_drives_results = Job_Drives.query.filter_by(status='Expired', creater_id = current_user.user_id)
        jobs = []
        for job in job_drives_results:
            company = Companies.query.filter_by(id=job.company_id).first()
            jobs.append([company.company_name, job, company.logo_path])

        return render_template('Job_drive.html', Jobs=jobs)

    search = request.args.get("search", "").strip()
    search_by = request.args.get("search_by", "company_name")

    query = Job_Drives.query.filter(Job_Drives.status != 'Closed')

    if search:
        if search_by == "company_name":
            query = query.join(Companies, Job_Drives.company_id == Companies.id).filter(
                Companies.company_name.ilike(f"%{search}%"), Job_Drives.creater_id == current_user.user_id)
        elif search_by == "title":
            query = query.filter(Job_Drives.title.ilike(f"%{search}%"), Job_Drives.creater_id == current_user.user_id)
        elif search_by == "Location":
            query = query.filter(Job_Drives.location.ilike(f"%{search}%"), Job_Drives.creater_id == current_user.user_id)

        # Fixed: Use Job_Drives (capital D) for the model column
        job_drives_results = query.order_by(Job_Drives.title).all()

        jobs = []
        for job in job_drives_results:
            company = Companies.query.filter_by(id=job.company_id).first()
            jobs.append([company.company_name, job, company.logo_path])

        return render_template('Job_drive.html', Jobs=jobs)

    job_drives_results = Job_Drives.query.filter_by(status = 'Active', creater_id = current_user.user_id).all()
    jobs = []
    for job in job_drives_results:
        company = Companies.query.filter_by(id=job.company_id).first()
        jobs.append([company.company_name, job, company.logo_path])

    return render_template('Job_drive.html', Jobs=jobs)


@Recruiter_bp.route('/Schedule_Interview', methods=['GET', 'POST'])
@login_required
def Schedule_Interview():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden
    student_id = request.form.get('student_id')
    drive_id = request.form.get('drive_id')
    application_id = request.form.get('application_id')
    if int(drive_id) not in [row[0] for row in db.session.query(Job_Drives.id).filter(Job_Drives.creater_id == current_user.user_id).all()] and Applications.query.filter(Applications.student_id == student_id, Applications.id == application_id, Applications.drive_id == drive_id).first() is None:
        abort(403)
    return render_template('Recruiter_Schedule_Interview.html', student_id = student_id, drive_id = drive_id)


@Recruiter_bp.route('/Recruiter_Application', methods=['GET', 'POST'])
@login_required
def Recruiter_Application():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden
    Job_drives = Job_Drives.query.filter(Job_Drives.creater_id == current_user.user_id, Job_Drives.status != 'Closed' )
    jobs = []
    for job in Job_drives:
        company = Companies.query.filter_by(id=job.company_id).first()
        jobs.append([company.company_name, job, company.logo_path])

    if request.method == 'POST':

        if request.args.get('mode') == 'update':

            appication = Applications.query.filter_by(student_id = request.form.get('student_id'), drive_id = request.form.get('drive_id')).first()
            student = Students.query.filter_by(id = request.form.get('student_id')).first()
            job = Job_Drives.query.filter_by(id = request.form.get('drive_id')).first()

            if appication.status.value == 'Applied':
                appication.status = 'SHORTLISTED'
                notifications(['shortlisted', student.user.email, job.company.company_name, job.title])
                notifications(['student_shortlisted_placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], student.user.name, job.company.company_name, job.title])
            elif appication.status.value == 'Interview Scheduled' and request.form.get('result') == 'Select':
                appication.status = 'SELECTED'
                notifications(['selected',student.user.email, job.company.company_name, job.title])
                notifications(['student_selected_placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], student.user.name, job.company.company_name, job.title])
            elif appication.status.value == 'Interview Scheduled' and request.form.get('result') == 'Reject':
                appication.status = 'REJECTED'
                notifications(['rejected',student.user.email, job.company.company_name, job.title])
                notifications(['student_rejected_placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], student.user.name, job.company.company_name, job.title])
            else:
                pass
            db.session.commit()

        elif request.args.get('mode') == 'schedule_interview':
            student_id = request.form.get('student_id')
            drive_id = request.form.get('drive_id')
            Round_Name = request.form.get('Round_Name')
            Interview_Date = request.form.get('Interview_Date')
            link = request.form.get('link')
            interview = Interview_Rounds(application_id=db.session.query(Applications.id).filter(Applications.student_id == student_id, Applications.drive_id == drive_id).scalar(), round_name=Round_Name, date=Interview_Date, link = link)
            appication = Applications.query.filter_by(student_id = student_id, drive_id = drive_id).first()
            appication.status = 'INTERVIEW'
            db.session.add(interview)
            db.session.commit()
            student = Students.query.filter(Students.id == student_id).first()
            job = Job_Drives.query.filter_by(id = drive_id).first()
            notifications(['Schedule_interview',student.user.email, job.company.company_name, job.title, Round_Name, Interview_Date])
            notifications(['student_interview_scheduled_placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], student.user.name, job.company.company_name, job.title, Round_Name, Interview_Date])

        else:
            pass

        job_id = request.form.get('drive_id')
        job1 = []
        job = Job_Drives.query.filter_by(id = job_id, creater_id = current_user.user_id).first()
        company = Companies.query.filter_by(id=job.company_id).first()
        job1.extend([company.company_name, job])

        Application = Applications.query.filter_by(drive_id = job_id).all()
        applicants = []
        for app in Application:
            student =  Students.query.filter(Students.id == app.student_id).first()
            if student.branch in job.Eligible_Branches and str(student.graduation_year) in job.Graduation_Year and student.cgpa >= float(job.CGPA):
                eligibility = 'Eligible'
            else:
                eligibility = 'Not Eligible'

            applicants.append([app,db.session.query(Users.name).filter(Users.user_id == (db.session.query(Students.user_id).filter(Students.id == app.student_id).scalar())).scalar(), Students.query.filter(Students.id == app.student_id).first(), eligibility])

        return render_template('Recruiter_Applicants.html', applicants=applicants, job = job1)

    return render_template('Recruiter_Application.html', Jobs=jobs)


@Recruiter_bp.route("/recruiter/certification/download", methods = ['GET','POST'])
@login_required
def download_certifications():
    if current_user.role not in [ "Recruiter","Placement_Officer" ]:
        abort(403)  # Forbidden
    name = request.form.get('name')
    filename = f"Cert_{request.form.get('id')}_{db.session.query(Users.name).filter(Users.user_id == int(request.form.get('id'))).scalar()}_{name}"
    RESUME_FOLDER = os.path.join(current_app.root_path, "static", "Docs", "student", "certifications")
    return send_from_directory(directory=RESUME_FOLDER, path=secure_filename(filename), as_attachment=True, download_name=name)


@Recruiter_bp.route("/student/resume/download", methods = ['GET', 'POST'])
@login_required
def download_resume():
    if current_user.role not in ["Recruiter", "Placement_Officer"]:
        abort(403)

    student = Students.query.filter_by(id = request.form.get("id")).first_or_404()

    if not student.resume_path:
        abort(404)

    RESUME_FOLDER = os.path.join(current_app.root_path, "static", "Docs", "student", "resumes")

    filename = secure_filename(student.resume_path)

    return send_from_directory(
        directory=RESUME_FOLDER,
        path=filename,
        as_attachment=True,
        download_name=student.resume_path
    )


@Recruiter_bp.route('/Job_drive/edit', methods=['GET', 'POST'])
@login_required
def edit_Job_drive():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden

    job_id = request.args.get('id')
    job = Job_Drives.query.filter_by(id = job_id, creater_id = current_user.user_id).first()

    if job is None:
        abort(403)

    if request.method == 'POST':
        if request.form.get('company_id'):
            job.company_id = request.form.get('company_id')
        if request.form.get('Title'):
            job.title = request.form.get('Title')
        if request.form.get('Package'):
            job.package = request.form.get('Package')
        if request.form.get('Location'):
            job.location = request.form.get('Location')
        if request.form.get('CGPA'):
            job.CGPA = request.form.get('CGPA')
        if request.form.getlist('Branches'):
            job.Eligible_Branches = ",".join(request.form.getlist('Branches'))
        if request.form.get('Graduation_Year'):
            job.Graduation_Year = request.form.get('Graduation_Year')
        if request.form.get('Vacancies'):
            job.Vacancies = request.form.get('Vacancies')
        if request.form.get('Deadline'):
            if datetime.datetime.strptime(request.form.get('Deadline'), '%Y-%m-%d').date() < datetime.date.today():
                flash("Deadline cannot be less than today", "deadline")
                return redirect(url_for('Recruiter.edit_Job_drive',id=job_id))
            job.deadline = request.form.get('Deadline')

        if request.form.get('Description'):
            job.description = request.form.get('Description')
        db.session.commit()
        return redirect(url_for('Recruiter.Job_drive'))

    compnaies = Companies.query.all()
    list1 = []
    for company in compnaies:
        list1.append([company.id, company.company_name])

    return render_template('Add_Job_drive.html', companies = list1, mode = 'edit', job_drive = job)


@Recruiter_bp.route('/Job_drive/add', methods=['GET', 'POST'])
@login_required
def add_Job_drive():
    if current_user.role != "Recruiter":
        abort(403)  # Forbidden
    if request.method == 'POST':
        company_id = request.form.get('company_id')
        Job_Title = request.form.get('Title')
        Package = request.form.get('Package')
        Location = request.form.get('Location')
        Minimum_CGPA = request.form.get('CGPA')
        Eligible_Branches = ",".join(request.form.getlist('Branches'))
        Graduation_Year = request.form.get('Graduation_Year')
        Vacancies = request.form.get('Vacancies')
        Deadline = request.form.get('Deadline')
        if datetime.datetime.strptime(request.form.get('Deadline'), '%Y-%m-%d').date() < datetime.date.today():
            flash("Deadline cannot be less than today", "deadline")
            return redirect(url_for('Recruiter.add_Job_drive'))
        Job_Description = request.form.get('Description')
        job_drive = Job_Drives(company_id = company_id, title = Job_Title, package = Package, location = Location, CGPA = Minimum_CGPA, Eligible_Branches = Eligible_Branches, Graduation_Year = Graduation_Year, Vacancies = Vacancies, deadline = Deadline, description = Job_Description, creater_id = current_user.user_id, application_count_email = {"email_count": 0, "student_id": []})
        db.session.add(job_drive)
        db.session.commit()

        notifications(['recruiter_job_drive_create', [user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()],job_drive, db.session.query(Companies.company_name).filter(Companies.id == company_id).scalar()])
        return redirect(url_for('Recruiter.Job_drive'))

    compnaies = Companies.query.all()
    list1 = []
    for company in compnaies:
        list1.append([company.id, company.company_name])
    return render_template('Add_Job_drive.html', companies = list1)


@Recruiter_bp.route('/Job_drive/delete', methods=['GET', 'POST'])
@login_required
def delete_Job_drive():
    if current_user.role != "Recruiter":
        abort(403)
    job_id = request.args.get('id')
    job = Job_Drives.query.filter_by(id = job_id, creater_id = current_user.user_id).first()
    if job is None:
        abort(403)
    job.status = 'Closed'
    db.session.commit()
    return redirect(url_for('Recruiter.Job_drive'))


@Recruiter_bp.route('/Student_Profile_Recruiter', methods=['GET', 'POST'])
@login_required
def Student_Profile_Recruiter():
    if current_user.role not in["Recruiter", "Placement_Officer"]:
        abort(403)
    user = Students.query.filter_by(id = request.form.get("id")).first()
    application_id = request.form.get('application_id')
    certs_list = [x.strip() for x in user.Certification.split(',') if x.strip()] if user.Certification else None
    certifications = certs_list if certs_list else None
    student = []
    student.extend([db.session.query(Users.name).filter(Users.user_id == user.user_id).scalar(),user])
    interview_rounds = Interview_Rounds.query.filter_by(application_id = application_id).all()
    if current_user.role == 'Recruiter':
        return render_template('Student_Profile_Recruiter.html', student=student, certifications=certifications,
                               application_id=application_id, interview_rounds=interview_rounds)
    elif current_user.role == 'Placement_Officer':
        return render_template('Student_Profile_Recruiter.html', student=student, certifications=certifications,
                               application_id=application_id, interview_rounds=interview_rounds)


@Recruiter_bp.route('/Recruiter_Interview', methods=['GET', 'POST'])
@login_required
def Recruiter_Interview():
    if current_user.role != "Recruiter":
        abort(403)
    if request.method == 'POST':
        round_id = request.form.get('round_id')
        mode = request.form.get('mode','')
        round = Interview_Rounds.query.filter_by(id = round_id).first()

        if mode == 'feedback':
            job_drive = Job_Drives.query.filter_by(creater_id=current_user.user_id).all()
            inner_query = db.session.query(Applications.id).filter(Applications.drive_id.in_([x.id for x in job_drive])).scalar_subquery()
            interview_rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(inner_query)).all()
            today_interview = []
            upcoming_interview = []
            for round in interview_rounds:
                if round.date.date() == datetime.date.today():
                    today_interview.append(
                        [round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.Application.student.user.name, round])
                elif round.date.date() >= datetime.date.today():
                    upcoming_interview.append(
                        [round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.Application.student.user.name, round])

            return render_template('Recruiter_Interview.html', mode = 'feedback',  today_interview = today_interview, upcoming_interview = upcoming_interview, round_id = round_id)

        elif mode == 'submit_feedback':
            feedback = request.form.get('feedback')
            round.feedback = feedback
            db.session.commit()
            return redirect(url_for('Recruiter.Recruiter_Interview'))

        result = request.form.get('result')
        round.result = result

        if result == 'Cleared':
            notifications(['Cleared', round.Application.student.user.email, round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.round_name])
            notifications(['student_cleared_placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], round.Application.student.user.name, round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.round_name])
        elif result == 'Rejected':
            application = Applications.query.filter_by(id = round.application_id).first()
            application.status = Application_status.REJECTED
            notifications(['rejected', round.Application.student.user.email, round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title])
            notifications(['student_rejected_round_placement_officer',
                       [user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()],
                       round.Application.student.user.name, round.Application.Job_Drive.company.company_name,
                       round.Application.Job_Drive.title, round.round_name])

        db.session.commit()
        return redirect(url_for('Recruiter.Recruiter_Interview'))

    job_drive = Job_Drives.query.filter_by(creater_id = current_user.user_id).all()

    inner_query = db.session.query(Applications.id).filter(Applications.drive_id.in_([x.id for x in job_drive])).scalar_subquery()

    interview_rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(inner_query)).all()

    today_interview = []
    upcoming_interview = []
    for round in interview_rounds:
        if round.date.date() == datetime.date.today():
            today_interview.append([round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.Application.student.user.name, round])
        elif round.date.date() >= datetime.date.today():
            upcoming_interview.append([round.Application.Job_Drive.company.company_name, round.Application.Job_Drive.title, round.Application.student.user.name, round])

    return render_template('Recruiter_Interview.html', today_interview = today_interview, upcoming_interview = upcoming_interview)
