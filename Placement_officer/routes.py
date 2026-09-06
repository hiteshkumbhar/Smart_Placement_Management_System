from flask import render_template, request, redirect, flash, url_for, abort, send_from_directory, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Users, Students, Companies, Job_Drives, Application_status, Applications, Interview_Rounds
import os
import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
from . import officer_bp
from utils.notifications import notifications
from sqlalchemy import func
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus.flowables import HRFlowable


@officer_bp.route('/Placement_officer_dashboard')
@login_required
def Placement_officer_dashboard():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden

    total_students = Students.query.filter_by(graduation_year=datetime.datetime.now(ZoneInfo("Asia/Kolkata")).year).count()
    placed_students = db.session.query(Applications.student_id).join(Students, Applications.student_id == Students.id).filter(Students.graduation_year == datetime.datetime.now(ZoneInfo("Asia/Kolkata")).year, Applications.status == Application_status.SELECTED).distinct().count()
    if total_students == 0:
        percentage = 0.0
    else:
        percentage = (placed_students / total_students) * 100

    unverified_resumes_count = Students.query.filter(Students.resume_status.in_(['Pending', 'Reuploaded','Rejected']),Students.resume_path.isnot(None), Students.graduation_year == datetime.datetime.now(ZoneInfo("Asia/Kolkata")).year).count()

    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    start_of_today = now_ist.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    start_of_tomorrow = start_of_today + timedelta(days=1)
    today_interview = Interview_Rounds.query.filter(Interview_Rounds.date >= start_of_today,Interview_Rounds.date < start_of_tomorrow).count()

    Posted_job_drive_count = Job_Drives.query.filter(Job_Drives.posted == 'Y', Job_Drives.status != 'Closed').count()

    Posted_job_drives = Job_Drives.query.filter(Job_Drives.posted == 'Y', Job_Drives.status != 'Closed').order_by(Job_Drives.deadline.asc()).limit(5).all()
    Posted_job_drive = []
    for job in Posted_job_drives:
        Posted_job_drive.append([job.company.company_name,job,Applications.query.filter(Applications.drive_id == job.id).count()])

    New_job_drives = Job_Drives.query.filter(Job_Drives.posted == 'N').order_by(Job_Drives.deadline.asc()).limit(5).all()

    return render_template('Placement_officer_dashboard.html', placement_percentage = percentage, unverified_resumes_count = unverified_resumes_count, today_interview_count = today_interview, Posted_job_drive_count = Posted_job_drive_count, Posted_job_drive = Posted_job_drive, New_job_drive = New_job_drives)


@officer_bp.route('/Placement_officer_Recruiter_Job_drive')
@login_required
def Placement_officer_Recruiter_Job_drive():
    if current_user.role != "Placement_Officer":
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
        Job_drives = Job_Drives.query.filter(Job_Drives.posted == 'N', Job_Drives.status == 'Expired', Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).all()
        jobs = []
        for job in Job_drives:
            company = Companies.query.filter_by(id=job.company_id).first()
            jobs.append([company.company_name, job, company.logo_path])
        return render_template('Placement_officer_Recruiter_Job_drive.html', Jobs=jobs)

    Job_drives = Job_Drives.query.filter(Job_Drives.posted=='N',Job_Drives.status == 'Active', Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).all()
    jobs = []
    for job in Job_drives:
        company = Companies.query.filter_by(id=job.company_id).first()
        jobs.append([company.company_name, job, company.logo_path])
    return render_template('Placement_officer_Recruiter_Job_drive.html',Jobs = jobs)


@officer_bp.route('/Placement_officer_Job_drive', methods = ['GET', 'POST'])
@login_required
def Placement_officer_Job_drive():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden

    mode = request.form.get('mode','')
    if mode == 'view' and request.method == 'POST':
        job_id = request.form.get('drive_id')
        job = Job_Drives.query.filter(Job_Drives.id == str(job_id), Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).first()
        company = Companies.query.filter_by(id=job.company_id).first()
        students = Students.query.all()
        opted_out_students = job.opt_out.split(',') if job.opt_out is not None else []

        Applicants = []

        for student in students:
            Application = Applications.query.filter_by(drive_id=job.id, student_id=student.id).first()
            if Application:
                Applicants.append([student.University_Roll_Number, db.session.query(Users.name).filter(Users.user_id == student.user_id).scalar(),student.branch,student.cgpa,Application.applied_at.strftime('%d-%m-%Y %H:%M'), Application.status, student.id, Application.id])
            elif student.job_drive and str(job.id) in student.job_drive:
                status = 'Recommended'
                Applicants.append([student.University_Roll_Number, db.session.query(Users.name).filter(Users.user_id == student.user_id).scalar(),student.branch,student.cgpa,'Not applied Yet', status, student.id, '0'])
            elif str(student.id) in opted_out_students:
                status = 'Opted out'
                Applicants.append([student.University_Roll_Number, db.session.query(Users.name).filter(Users.user_id == student.user_id).scalar(),student.branch,student.cgpa,'Not applied', status, student.id, '0'])
        jobs = [company.company_name,job,company.logo_path]
        return render_template('Placement_officer_Job_drive.html', jobs = jobs, Applicants = Applicants, mode = mode)

    posted_jobs = Job_Drives.query.filter(Job_Drives.posted == 'Y', Job_Drives.status != 'Closed', Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).all()
    jobs = []
    for job in posted_jobs:
        company = Companies.query.filter_by(id=job.company_id).first()
        jobs.append([company.company_name, job, company.logo_path])
    return render_template('Placement_officer_Job_drive.html', jobs = jobs, mode = mode)


@officer_bp.route('/Placement_Officer_Interview', methods = ['GET','POST'])
@login_required
def Placement_Officer_Interview():

    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden

    rounds = Interview_Rounds.query.all()

    today_search = request.form.get('today_search')
    upcoming_search = request.form.get('upcoming_search')
    past_search = request.form.get('past_search')

    Todays_interview = []
    upcoming_interviews = []
    Past_interviews = []

    for r in rounds:
        if r.date.date() == datetime.date.today():
            if today_search:
                if today_search.lower() in r.Application.Job_Drive.company.company_name.lower() or today_search.lower() in r.Application.student.user.name.lower():
                    Todays_interview.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])
            else:
                Todays_interview.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])
        elif r.date.date() > datetime.date.today():
            if upcoming_search:
                if upcoming_search.lower() in r.Application.Job_Drive.company.company_name.lower() or upcoming_search.lower() in r.Application.student.user.name.lower():
                    upcoming_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])
            else:
                upcoming_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])
        else:
            if past_search:
                if past_search.lower() in r.Application.Job_Drive.company.company_name.lower() or past_search.lower() in r.Application.student.user.name.lower():
                    Past_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])
            else:
                Past_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title,r.Application.student.user.name, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path,r.id])

    return render_template('Placement_Officer_Interview.html', Todays_interview=Todays_interview, upcoming_interviews=upcoming_interviews, Past_interviews=Past_interviews)


@officer_bp.route('/students', methods = ['GET','POST'])
@login_required
def Placement_officer_student():
    if current_user.role != "Placement_Officer":
        abort(403)

    students = Students.query.all()
    graduation_years = sorted({student.graduation_year for student in students if student.graduation_year is not None})
    branches = sorted({student.branch for student in students if student.branch is not None})

    if request.args.get('Search') is not None:
        search = request.args.get('Search')
        students = Students.query.filter(Students.user.has(Users.name.ilike(f"%{search}%"))).all()
        return render_template('Placement_officer_student.html', students=students, graduation_years = graduation_years, branches = branches)

    if request.args.get('status') or request.args.get('graduation_year') or request.args.get('branch'):
        status = request.args.get('status')
        graduation_year = request.args.get('graduation_year')
        branch = request.args.get('branch')

        query = Students.query

        if status:
            query = query.filter(Students.resume_status == status)

        if graduation_year:
            query = query.filter(Students.graduation_year == graduation_year)

        if branch:
            query = query.filter(Students.branch == branch)

        students = query.all()
        return render_template('Placement_officer_student.html', students=students, graduation_years = graduation_years, branches = branches)

    if request.method == 'POST':
        student = Students.query.filter_by(id=request.form.get('Student_details')).first_or_404()
        applications = Applications.query.filter_by(student_id=request.form.get('Student_details')).all()
        student_drives = student.job_drive.split(',') if student.job_drive else None
        print(student_drives)
        opted_outs = [job for job in Job_Drives.query.all() if job.opt_out and str(request.form.get('Student_details')) in job.opt_out]
        apps = []
        if applications:
            for app in applications:
                apps.append([app.Job_Drive.company.company_name, app.Job_Drive.title, app.status.value, app.id])
        if student_drives:
            for drive in student_drives:
                student_job_drive = Job_Drives.query.filter(Job_Drives.id == int(drive.strip())).first()
                apps.append([student_job_drive.company.company_name, student_job_drive.title, 'Recommended'])
        if len(opted_outs) > 0:
            for j in opted_outs:
                apps.append([j.company.company_name, j.title, 'Opted Out'])

        if request.form.get('mode') == 'view_details':

            certifications = [x.strip() for x in student.Certification.split(
                ',')] if student.Certification and student.Certification.strip() else None

            return render_template('Placement_officer_student_details.html', student = student, certifications = certifications, graduation_years = graduation_years, branches = branches, applications = apps)

        elif request.form.get('mode') == 'resume_status':

            student = Students.query.filter_by(id = request.form.get('Student_details')).first_or_404()
            certifications = [x.strip() for x in student.Certification.split(',')] if student.Certification and student.Certification.strip() else None

            if request.form.get('action') == 'verify':
                student.resume_status = 'Verified'
                db.session.commit()
                notifications(['resumeverified',student.user.email])
            elif request.form.get('action') == 'reject':
                student.resume_status = 'Rejected'
                db.session.commit()
                notifications(['resumerejected',student.user.email, student.resume_remark])

            return render_template('Placement_officer_student_details.html', student = student, certifications = certifications, graduation_years = graduation_years, branches = branches, applications = apps)

        elif request.form.get('mode') == 'give_remark':

            student = Students.query.filter_by(id=request.form.get('Student_details')).first_or_404()

            certifications = [x.strip() for x in student.Certification.split(',')] if student.Certification and student.Certification.strip() else None

            if request.form.get('remark') != '':
                student.resume_remark = request.form.get('remark')
                db.session.commit()
                return render_template('Placement_officer_student_details.html', student=student, certifications=certifications, applications = apps)

            return render_template('Placement_officer_student_details.html', student = student, certifications = certifications, mode = 'remark', graduation_years = graduation_years, branches = branches, applications = apps)

        elif request.form.get('mode') == "placement_status":
            student = Students.query.filter_by(id=request.form.get('Student_details')).first_or_404()
            certifications = [x.strip() for x in student.Certification.split(',')] if student.Certification and student.Certification.strip() else None
            student.placement_status = 'Placed'
            db.session.commit()
            return render_template('Placement_officer_student_details.html', student=student, certifications=certifications, graduation_years = graduation_years, branches = branches, applications = apps )

    students = Students.query.all()
    return render_template('Placement_officer_student.html', students = students, graduation_years = graduation_years, branches = branches)


@officer_bp.route('/Analytics', methods = ['GET','POST'])
@login_required
def Placement_officer_analytics():
    if current_user.role != "Placement_Officer":
        abort(403)

    year = request.args.get('year')
    target_year = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).year if year is None else year
    total_students = Students.query.filter(Students.graduation_year == target_year).count()
    placed_students = db.session.query(Applications.student_id).join(Students, Applications.student_id == Students.id).filter(Students.graduation_year == target_year, Applications.status == Application_status.SELECTED).distinct().count()

    placed_student_ids = db.session.query(Applications.student_id).filter(Applications.status == Application_status.SELECTED).scalar_subquery()
    unplaced_students = Students.query.filter(Students.graduation_year == target_year,~Students.id.in_(placed_student_ids)).count()

    if total_students == 0:
        percentage = 0.0
    else:
        percentage = (placed_students / total_students) * 100

    highest_paying_job = Job_Drives.query.filter(func.extract('year', Job_Drives.deadline) == target_year).order_by(Job_Drives.package.desc()).first()

    average_package = db.session.query(func.avg(Job_Drives.package)).filter(func.extract('year', Job_Drives.deadline) == target_year).scalar()


    companies = Companies.query.all()
    company_names = []
    drive_counts = []
    for company in companies:
        count = Job_Drives.query.filter(Job_Drives.company_id == company.id,func.extract('year', Job_Drives.deadline) == target_year).count()
        if count > 0:
            company_names.append(company.company_name)
            drive_counts.append(count)

    branches_query = db.session.query(Students.branch).filter(Students.graduation_year == target_year).distinct().all()
    unique_branches = [b[0] for b in branches_query]
    branch_names = []
    placement_counts = []
    for branch in unique_branches:
        count = db.session.query(Students.id).join(Applications).filter(Students.branch == branch,Students.graduation_year == target_year,Applications.status == Application_status.SELECTED).distinct().count()
        branch_names.append(branch)
        placement_counts.append(count)


    resume_query = db.session.query(Students.resume_status,func.count(Students.id)).filter(Students.graduation_year == target_year).group_by(Students.resume_status).all()
    resume_labels = []
    resume_counts = []
    for status, count in resume_query:
        display_status = status if status else 'Not Uploaded'
        resume_labels.append(display_status)
        resume_counts.append(count)


    status_tracker = {Application_status.APPLIED.value: 0,Application_status.SHORTLISTED.value: 0,Application_status.INTERVIEW.value: 0,Application_status.SELECTED.value: 0,Application_status.REJECTED.value: 0}
    app_query = db.session.query(Applications.status,func.count(Applications.id)).join(Students, Applications.student_id == Students.id).filter(Students.graduation_year == target_year).group_by(Applications.status).all()
    for status, count in app_query:
        status_tracker[status.value] = count
    app_labels = list(status_tracker.keys())
    app_data = list(status_tracker.values())

    graduation_years = [r.graduation_year for r in Students.query.with_entities(Students.graduation_year).distinct().order_by(Students.graduation_year.desc()) if r.graduation_year is not None]

    return render_template('Placement_officer_analytics.html', total_students = total_students, placed_students = placed_students, unplaced_students = unplaced_students, percentage = percentage, highest_package = highest_paying_job.package if highest_paying_job is not None else 0, average_package = average_package if average_package is not None else 0, labels=company_names, data=drive_counts, branch_labels = branch_names, branch_data = placement_counts, resume_labels=resume_labels, resume_counts=resume_counts, app_labels=app_labels,
    app_data=app_data, graduation_years = graduation_years)


@officer_bp.route('/Companies_info', methods = ['GET','POST'])
@login_required
def Companies_info():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden

    mode = request.args.get('mode','ViewAll')
    search = request.args.get("search", "").strip()
    search_by = request.args.get("search_by", "company_name")
    query = Companies.query
    if search:
        if search_by == "company_name":
            query = query.filter(Companies.company_name.ilike(f"%{search}%"), Companies.creater_id == current_user.user_id)

        elif search_by == "industry":
            query = query.filter(Companies.industry.ilike(f"%{search}%"), Companies.creater_id == current_user.user_id)

        elif search_by == "hr_name":
            query = query.filter(Companies.hr_name.ilike(f"%{search}%"), Companies.creater_id == current_user.user_id)

        companies = query.order_by(Companies.company_name).all()

        a = []

        for company in companies:
            a.append([company.company_name, company.logo_path, company.industry, company.website, company.hr_name,
                      company.phone, company.email, company.address,
                      Job_Drives.query.filter(Job_Drives.company_id == company.id, Job_Drives.status != 'Closed').count(), company.id])
        return render_template('Companies_info.html', companies=a, mode=mode)

    companies = Companies.query.filter(Companies.creater_id == current_user.user_id).all()
    a = []
    for company in companies:
        a.append([company.company_name, company.logo_path, company.industry, company.website, company.hr_name,  company.phone, company.email,company.address, Job_Drives.query.filter(Job_Drives.company_id == company.id).count() ,company.id])
    if mode == 'view':
        t_company =  Companies.query.filter(Companies.id == request.args.get('id'), Companies.creater_id == current_user.user_id).first()
        if t_company is None:
            abort(403)
        target_company = [t_company.company_name, t_company.logo_path, t_company.industry, t_company.website, t_company.hr_name, t_company.phone, t_company.email, t_company.address, Job_Drives.query.filter(Job_Drives.company_id == t_company.id).count(), t_company.id]
        return render_template('Companies_info.html', companies=a, mode=mode, target_company = target_company)

    return render_template('Companies_info.html', companies = a, mode = mode)


@officer_bp.route('/Company/edit', methods = ['GET','POST'])
@login_required
def edit_company():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden
    company_id = request.args.get('id', type=int)
    company = Companies.query.filter(Companies.id == company_id, Companies.creater_id == current_user.user_id).first()
    if company is None:
        abort(403)

    if request.method == 'POST':
        company = Companies.query.filter(Companies.id == company_id, Companies.creater_id == current_user.user_id).first()
        if company is None:
            abort(403)

        if request.form.get('name'):
            company.company_name = request.form.get('name')
        if request.form.get('Industry'):
            company.industry = request.form.get('Industry')
        if request.form.get('website'):
            company.website = request.form.get('website')
        if request.form.get('HR_Name'):
            company.hr_name = request.form.get('HR_Name')
        if request.form.get('HR_Email'):
            company.email = request.form.get('HR_Email')
        if request.form.get('HR_number'):
            company.phone = request.form.get('HR_number')
        if request.form.get('Address'):
            company.address = request.form.get('Address')

        MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
        logo = request.files.get('Logo')
        logo.seek(0, os.SEEK_END)
        file_size = logo.tell()
        logo.seek(0)

        if logo and logo.filename != '':
            file_extension = logo.filename.rsplit('.', 1)[1].lower()
            if file_extension in ['jpg', 'jpeg', 'png'] and file_size < MAX_FILE_SIZE_BYTES:
                FOLDER = os.path.join('static', 'Images', 'company', 'logo')
                os.makedirs(FOLDER, exist_ok=True)

                filename = logo.filename
                filepath = os.path.join(FOLDER, filename)
                logo.save(filepath)
                company.logo_path = logo.filename
            else:
                if file_extension not in ['jpg', 'jpeg', 'png']:
                    flash('Upload file in jpg or jpeg or png format', 'profile_pic')
                if file_size > MAX_FILE_SIZE_BYTES:
                    flash('Logo size must be less that 5 mb', 'Logo_size_error')
                return redirect(url_for('Placement_officer.edit_company',id = company_id) )

        db.session.commit()
        return redirect(url_for('Placement_officer.Companies_info'))

    return render_template('add_company.html', mode = 'edit', company = company)


@officer_bp.route('/Company/delete', methods = ['GET','POST'])
@login_required
def delete_company():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden
    company_id = request.args.get('id', type=int)
    company = Companies.query.filter(Companies.id == company_id, Companies.creater_id == current_user.user_id).first()
    if company is None:
        abort(403)
    db.session.delete(company)
    db.session.commit()
    return redirect(url_for('Placement_officer.Companies_info'))


@officer_bp.route('/Company/add', methods = ['GET','POST'])
@login_required
def add_company():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden
    if request.method == 'POST':
        name = request.form.get('name')
        industry = request.form.get('Industry')
        website = request.form.get('website')
        HR_Name = request.form.get('HR_Name')
        HR_Email = request.form.get('HR_Email')
        HR_number = request.form.get('HR_number')
        Address = request.form.get('Address')

        MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
        logo = request.files.get('Logo')
        logo.seek(0, os.SEEK_END)
        file_size = logo.tell()
        logo.seek(0)

        if logo and logo.filename != '':
            file_extension = logo.filename.rsplit('.', 1)[1].lower()
            if file_extension in ['jpg', 'jpeg', 'png'] and file_size < MAX_FILE_SIZE_BYTES:
                FOLDER = os.path.join('static', 'Images', 'company', 'logo')
                os.makedirs(FOLDER, exist_ok=True)

                filename = logo.filename
                filepath = os.path.join(FOLDER, filename)
                logo.save(filepath)

            else:
                if file_extension not in ['jpg', 'jpeg', 'png']:
                    flash('Upload file in jpg or jpeg or png format', 'profile_pic')
                if file_size > MAX_FILE_SIZE_BYTES:
                    flash('Logo size must be less that 5 mb', 'Logo_size_error')
                return redirect(url_for('Placement_officer.add_company'))

        company = Companies(company_name = name, industry=industry, website=website, hr_name=HR_Name, email=HR_Email, phone = HR_number, logo_path =  secure_filename(logo.filename), address = Address, created_at = datetime.datetime.now(ZoneInfo("Asia/Kolkata")), creater_id = current_user.user_id)
        db.session.add(company)
        db.session.commit()
        return redirect(url_for('Placement_officer.Companies_info'))

    return render_template('add_company.html')


@officer_bp.route('/Post_Job_Drive', methods=['GET', 'POST'])
@login_required
def Post_Job_Drive():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden

    job_id = request.values.get('drive_id')

    if request.args.get('mode','N') == 'post_job_drive':
        job = Job_Drives.query.filter(Job_Drives.id == job_id, Job_Drives.company_id.in_(
            db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).first()
        if job is None:
            abort(403)

        company = Companies.query.filter_by(id=job.company_id).first()

        job1 = []
        job1.extend([company.company_name, job])

        eligible_students = Students.query.filter(Students.cgpa >= job.CGPA,Students.branch.in_(job.Eligible_Branches.split(',')),Students.graduation_year.in_(job.Graduation_Year.split(','))).all()

        E_Students = []
        for i in eligible_students:
            E_Students.append([i.id, db.session.query(Users.name).filter(Users.user_id == i.user_id).scalar()])

        All_students = []
        Student = Students.query.all()
        for j in Student:
            All_students.append([j.id, db.session.query(Users.name).filter(Users.user_id == j.user_id).scalar()])

        return render_template('Post_Job_Drive.html', job=job1, eligible_students=E_Students, All_Student=All_students,
                               job_id=job_id)

    if request.method == 'POST':

        S1 = request.form.getlist('Students')
        S2 = request.form.getlist('All_Students')
        S1.extend(S2)

        job = Job_Drives.query.filter(Job_Drives.id == job_id, Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).first()
        flag = 0
        for i in S1:
            Student = Students.query.filter_by(id = i).first()
            if not Applications.query.filter_by(student_id = Student.id, drive_id = job_id).first():
                if Student.job_drive is None or str(job_id) not in Student.job_drive:
                    if job.opt_out is None or str(Student.id) not in job.opt_out:
                        if Student.job_drive == None:
                            Student.job_drive = job_id
                            notifications(['Postjobdrive',Student.user.email, job.company.company_name, job.title, job.package, job.deadline])
                        else:
                            Student.job_drive = Student.job_drive + ',' + job_id
                            notifications(['Postjobdrive',Student.user.email, job.company.company_name, job.title, job.package, job.deadline])
                    else:
                        list1 = job.opt_out.split(',')
                        list1.remove(str(Student.id))
                        job.opt_out = ','.join(list1)
                        if Student.job_drive == None:
                            Student.job_drive = job_id
                            notifications(['Postjobdrive',Student.user.email, job.company.company_name, job.title, job.package, job.deadline])
                        else:
                            Student.job_drive = Student.job_drive + ',' + job_id
                            notifications(['Postjobdrive',Student.user.email, job.company.company_name, job.title, job.package, job.deadline])
                else:
                    flash(f'Student {db.session.query(Users.name).filter(Users.user_id == Student.user_id).scalar()} is already recommended',
                        'Duplicate_recommendation_error')
                    flag = 1
            else:
                flash(f'Application of {db.session.query(Users.name).filter(Users.user_id == Student.user_id).scalar()} already exist','Duplicate_Application')
                flag = 1
            db.session.commit()
        if flag == 1:
            return redirect(url_for('Placement_officer.Post_Job_Drive', mode='post_job_drive', drive_id=job_id))
        job = Job_Drives.query.filter(Job_Drives.id == job_id, Job_Drives.company_id.in_(db.session.query(Companies.id).filter(Companies.creater_id == current_user.user_id))).first()
        job.posted = 'Y'
        db.session.commit()

        return redirect(url_for('Placement_officer.Placement_officer_Recruiter_Job_drive'))


@officer_bp.route('/Reports', methods=['GET', 'POST'])
@login_required
def Reports():
    if current_user.role != "Placement_Officer":
        abort(403)  # Forbidden
    report = request.args.get('report', 'student_report')
    if report == 'student_report':

        if request.method == 'POST':
            Branch = request.form.get('Branch')
            Year = request.form.get('Year')
            Resume_Status = request.form.get('Resume_Status')
            Placement_Status = request.form.get('Placement_Status')

            query = Students.query
            if Branch:
                query = query.filter(Students.branch == Branch)
            if Year:
                Year = int(Year)
                query = query.filter(Students.graduation_year == Year)
            if Resume_Status:
                query = query.filter(Students.resume_status == Resume_Status)
            if Placement_Status:
                query = query.filter(Students.placement_status == Placement_Status)

            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("ABC COLLEGE OF ENGINEERING", styles['Title']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(Paragraph("Placement Cell – Student Report", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph(f"Generated By : {current_user.name}", styles['Normal']))
            elements.append(Paragraph(f"Generated On : {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", styles['Normal']))
            elements.append(Paragraph(f"Branch: {Branch if Branch != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Graduation: {Year if Year != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Resume Status: {Resume_Status if Resume_Status != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Placement Status: {Placement_Status if Placement_Status != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("STUDENT DETAILS", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))

            table_data = [['Roll No', 'Student Name', 'Branch', 'CGPA', 'Resume', 'Placement', 'Company']]
            for student in query:
                table_data.append([student.University_Roll_Number, student.user.name, student.branch, student.cgpa, student.resume_status, 'Not Placed' if student.placement_status == 'Open to Placement' else student.placement_status, ", ".join([app.Job_Drive.company.company_name for app in student.Application if app.status == Application_status.SELECTED]) or "-"])
            report_table = Table(table_data)
            style = TableStyle([
                # Header Row Styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Body Styling (Applies to ALL data rows, including the last one)
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),

                # Grid and Borders
                # Changed from (-1, -2) to (-1, -1) so the grid covers the entire table
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("Summary", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Total Students         : {query.count()}", styles['Normal']))

            if not Branch:
                branches = [row.branch for row in db.session.query(Students.branch).distinct().all()]
                for branch in branches:
                    elements.append(Paragraph(f"{branch} Students         : {query.filter(Students.branch == branch).count()}", styles['Normal']))
            else:
                elements.append(Paragraph(f"{Branch} Students         : {query.count()}",styles['Normal']))

            if not Resume_Status:
                status = ['Verified', 'Rejected', 'Pending', 'Reuploaded']
                for Y in status:
                    elements.append(Paragraph(f"Resume {Y}        : {query.filter(Students.resume_status == Y).count()}", styles['Normal']))
            else:
                elements.append(Paragraph(f"Resume {Resume_Status}        : {query.count()}",styles['Normal']))

            if not Placement_Status:
                placement_stats = ['Open to Placement', 'Placed']
                for P in placement_stats:
                    if P == 'Placed':
                        elements.append(Paragraph(f"Placed students        : {query.filter(Students.placement_status == P).count()}", styles['Normal']))
                    elif P == 'Open to Placement':
                        elements.append(Paragraph(f"Unplaced students        : {query.filter(Students.placement_status == P).count()}", styles['Normal']))
            else:
                if Placement_Status == 'Placed':
                    elements.append(Paragraph(f"Placed students        : {query.count()}",styles['Normal']))
                else:
                    elements.append(Paragraph(f"Unplaced students        : {query.count()}",styles['Normal']))

            if not Resume_Status and not Placement_Status:
                total = query.count()
                placed = query.filter(Students.placement_status == 'Placed').count()
                Placement_percentage = round((placed / total) * 100, 1) if total > 0 else 0
                elements.append(Paragraph(f"Placement Percentage   :{Placement_percentage} %",styles['Normal']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("<para align='center'>Generated by Smart Placement Management System</para>",
                                      styles['Normal']))
            pdf.build(elements)
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype="application/pdf",
                as_attachment=False,
                download_name="Student_Report.pdf"
            )


        branches = [row.branch for row in db.session.query(Students.branch).distinct().all() if row.branch is not None ]
        Years = [r.graduation_year for r in Students.query.with_entities(Students.graduation_year).distinct().order_by(Students.graduation_year.desc()) if r.graduation_year is not None]
        return render_template("Placement_officer_Reports.html", report=report, branches=branches, Years = Years)

    elif report == 'Company_Report':
        if request.method == 'POST':

            Company = request.form.get('company')
            Year = request.form.get('Year')
            Industry = request.form.get('Industry')

            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("ABC COLLEGE OF ENGINEERING", styles['Title']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(Paragraph("Placement Cell – Company Report", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph(f"Generated By : {current_user.name}", styles['Normal']))
            elements.append(Paragraph(f"Generated On : {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", styles['Normal']))
            elements.append(Paragraph(f"Company: {Company if Company != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Industry: {Industry if Industry != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Year: {Year if Year != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Company Details", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))

            query = Companies.query.filter(Companies.creater_id == current_user.user_id)
            if Industry:
                query = query.filter(Companies.industry == Industry)
            if Company:
                query = query.filter(Companies.company_name == Company)
            if Year:
                Job_drives = Job_Drives.query.join(Companies).filter(Companies.creater_id == current_user.user_id)
                Job_drives = Job_drives.filter(db.extract('year', Job_Drives.deadline) == int(Year)).all()
                comp_ids = list({job.company.id for job in Job_drives})
                query = query.filter(Companies.id.in_(comp_ids))

            query = query.all()

            style = TableStyle([
                # Header Row Stylingcreated_at
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Body Styling (Applies to ALL data rows, including the last one)
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),

                # Grid and Borders
                # Changed from (-1, -2) to (-1, -1) so the grid covers the entire table
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])

            table_data = [['Sr.', 'Company Name', 'Industry', 'HR Name', 'Email', 'Website']]
            count = 1
            for company in query:
                c_name = Paragraph(company.company_name or "", styles['Normal'])
                industry = Paragraph(company.industry or "", styles['Normal'])
                hr_name = Paragraph(company.hr_name or "", styles['Normal'])
                email = Paragraph(company.email or "", styles['Normal'])
                website = Paragraph(company.website or "", styles['Normal'])
                table_data.append([count, c_name, industry, hr_name, email, website])
                count += 1
            Total_comapnies = len(table_data) -1
            col_widths = [30, 90, 80, 90, 120, 110]

            # Pass the colWidths to the Table
            report_table = Table(table_data, colWidths=col_widths)
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("Recruitment Statistics", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))


            Job_drives = Job_Drives.query.join(Companies).filter(Companies.creater_id == current_user.user_id)
            if Industry:
                Job_drives = Job_drives.filter(Companies.industry == Industry)
            if Company:
                Job_drives = Job_drives.filter(Companies.company_name == Company)
            if Year:
                Job_drives = Job_drives.filter(db.extract('year', Job_Drives.deadline) == int(Year))
            Job_drives = Job_drives.all()

            distinct_companies = list({job.company.company_name for job in Job_drives})

            table_data = [['Sr.', 'Company', 'Drives', 'Applications', 'Shortlisted', 'Interviewed', 'Selected']]
            table_data2 = [['Sr.', 'Company', 'Highest CTC', 'Lowest CTC', 'Average CTC']]
            count = 1
            grand_total_selected = 0
            total_applications = 0
            for company in distinct_companies:
                total_apps = 0
                shortlisted = 0
                Interviewed = 0
                Selected = 0
                job_drives = set()
                drive_packages_dict = {}
                for job in Job_drives:
                    if job.company.company_name == company:
                        job_drives.add(job.id)
                        Apps = Applications.query.filter(Applications.drive_id == job.id).all()
                        total_applications += len(Apps)
                        total_apps += len(Apps)
                        if job.package is not None:
                            drive_packages_dict[job.id] = float(job.package)
                        for app in Apps:
                            if app.status == Application_status.SHORTLISTED:
                                shortlisted += 1
                            elif app.status == Application_status.INTERVIEW:
                                Interviewed += 1
                            elif app.status == Application_status.SELECTED:
                                Selected += 1
                valid_packages = list(drive_packages_dict.values())
                if valid_packages:
                    highest_ctc = max(valid_packages)
                    lowest_ctc = min(valid_packages)
                    avg_ctc = round(sum(valid_packages) / len(valid_packages), 2)
                else:
                    highest_ctc = 0
                    lowest_ctc = 0
                    avg_ctc = 0
                table_data.append([count, company, len(job_drives), total_apps, shortlisted, Interviewed, Selected])
                table_data2.append([count, company, highest_ctc, lowest_ctc, avg_ctc])
                count += 1
                grand_total_selected += Selected

            report_table = Table(table_data)
            report_table.setStyle(style)
            elements.append(report_table)

            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("Company-wise Package Details", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            report_table = Table(table_data2)
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("Summary", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Total Companies         : {Total_comapnies}", styles['Normal']))
            elements.append(Paragraph(f"Total Job Drives        : {len(Job_drives)}", styles['Normal']))
            elements.append(Paragraph(f"Total Applications      : {total_applications}", styles['Normal']))
            elements.append(Paragraph(f"Total Selected          : {grand_total_selected}", styles['Normal']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("<para align='center'>Generated by Smart Placement Management System</para>",
                                      styles['Normal']))
            pdf.build(elements)
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype="application/pdf",
                as_attachment=False,
                download_name="Student_Report.pdf"
            )
        Company_Name = [row.company_name for row in db.session.query(Companies.company_name).filter(Companies.creater_id == current_user.user_id).distinct().all()]
        Industry = [row.industry for row in db.session.query(Companies.industry).filter(Companies.creater_id == current_user.user_id).distinct().all()]
        Years = [r.graduation_year for r in Students.query.with_entities(Students.graduation_year).distinct().order_by(Students.graduation_year.desc()) if r.graduation_year is not None]
        return render_template("Placement_officer_Reports.html", report=report, Company_Name=Company_Name, Industry=Industry, Years = Years)

    elif report == 'Placement_Report':
        if request.method == 'POST':
            Company = request.form.get('company')
            Year = request.form.get('Year')
            branches = request.form.get('branches')

            buffer = io.BytesIO()
            pdf = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("ABC COLLEGE OF ENGINEERING", styles['Title']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(Paragraph("Placement Cell – Placement Report", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph(f"Generated By : {current_user.name}", styles['Normal']))
            elements.append(Paragraph(f"Generated On : {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", styles['Normal']))
            elements.append(Paragraph(f"Year: {Year if Year != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Branch: {branches if branches != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph(f"Company: {Company if Company != '' else 'All'}", styles['Normal']))
            elements.append(Paragraph("<br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"BRANCH-WISE PLACEMENT", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))

            style = TableStyle([
                # Header Row Styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

                # Body Styling (Applies to ALL data rows, including the last one)
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),

                # Grid and Borders
                # Changed from (-1, -2) to (-1, -1) so the grid covers the entire table
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            query = Students.query
            if Year:
                query = query.filter(Students.graduation_year == Year)
            if branches:
                query = query.filter(Students.branch == branches)
            if Company:
                student_ids = [row.student_id for row in
                               db.session.query(Applications.student_id).join(Job_Drives).join(Companies).filter(
                                   Companies.company_name == Company).distinct().all()]
                query = query.filter(Students.id.in_(student_ids))

            filtered_students = query.all()

            distinct_branches = list({s.branch for s in filtered_students})

            table_data = [['Sr.', 'Branch', 'Total Students', 'Applied', 'Placed', 'Percentage', 'Highest CTC']]
            count = 1
            grand_total = 0
            grand_total_selected = 0
            for BRANCH in distinct_branches:

                total_student = Students.query.filter(Students.branch == BRANCH)

                if Year:
                    total_student = total_student.filter(Students.graduation_year == int(Year))

                total_student = total_student.all()

                if Company:
                    total_applied = set()
                    selected_students = set()
                    all_package = set()
                    for student1 in total_student:
                        for app in student1.Application:
                            if app.Job_Drive.company.company_name == Company:
                                total_applied.add(student1.id)
                                if app.status == Application_status.SELECTED:
                                    selected_students.add(student1.id)
                                    all_package.add(app.Job_Drive.package)

                else:
                    total_applied = set()
                    selected_students = set()
                    all_package = set()
                    for student1 in total_student:
                        for app in student1.Application:
                            total_applied.add(student1.id)
                            if app.status == Application_status.SELECTED:
                                selected_students.add(student1.id)
                                all_package.add(app.Job_Drive.package)

                table_data.append([count, BRANCH, len(total_student), len(total_applied), len(selected_students), round(len(selected_students)*100/len(total_student), 2) if len(total_student) > 0 else 0, max(all_package) if len(all_package) > 0 else 0])
                grand_total += len(total_student)
                grand_total_selected += len(selected_students)
                count += 1

            report_table = Table(table_data)
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Company-wise Placement Summary", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            table_data = [['Sr.', 'Company', 'Drives', 'Selected', 'Highest CTC']]

            table_data2 = [['Sr.', 'Roll No.', 'Student Name', 'Branch', 'Company','Job Role','Package']]
            student_count = 1
            grand_total_job_drive = 0
            grand_total_applications = 0
            grand_total_packages = []
            if Company:
                jds = Job_Drives.query.join(Companies).filter(Companies.company_name == Company)
                if Year:
                    jds = jds.filter(func.extract('year', Job_Drives.deadline) == Year)
                if branches:
                    jds = jds.filter(Job_Drives.Eligible_Branches.ilike(f'%{branches}%'))
                jds = jds.all()
                count = 1
                selected1 = 0
                all_package = set()
                for job1 in jds:
                    for app in job1.Applications:
                        if branches:
                            if app.student.branch == branches:
                                grand_total_applications += 1
                                if app.status == Application_status.SELECTED :
                                    selected1 += 1
                                    table_data2.append([student_count, app.student.University_Roll_Number, app.student.user.name, app.student.branch, Company, app.Job_Drive.title, f'{app.Job_Drive.package} LPA' ])
                                    student_count += 1
                                    all_package.add(job1.package)
                                    grand_total_packages.append(job1.package)
                        else:
                            grand_total_applications += 1
                            if app.status == Application_status.SELECTED:
                                selected1 += 1
                                table_data2.append(
                                    [student_count, app.student.University_Roll_Number, app.student.user.name,
                                     app.student.branch, Company, app.Job_Drive.title, f'{app.Job_Drive.package} LPA'])
                                student_count += 1
                                all_package.add(job1.package)
                                grand_total_packages.append(job1.package)
                grand_total_job_drive += len(jds)
                table_data.append([count, Company, len(jds), selected1, f'{max(all_package) if len(all_package)>0 else 0} LPA'])
            else:
                companies = Companies.query.filter(Companies.creater_id == current_user.user_id)
                count = 1
                for company1 in companies:
                    jds = Job_Drives.query.filter(Job_Drives.company_id == company1.id)
                    if Year:
                        jds = jds.filter(func.extract('year', Job_Drives.deadline) == Year)
                    if branches:
                        jds = jds.filter(Job_Drives.Eligible_Branches.ilike(f'%{branches}%'))
                    jds = jds.all()
                    selected1 = 0
                    all_package = set()
                    for job1 in jds:
                        for app in job1.Applications:
                            if branches:
                                if app.student.branch == branches:
                                    grand_total_applications += 1
                                    if app.status == Application_status.SELECTED:
                                        selected1 += 1
                                        table_data2.append([student_count, app.student.University_Roll_Number, app.student.user.name, app.student.branch, company1.company_name, app.Job_Drive.title, f'{app.Job_Drive.package} LPA'])
                                        student_count += 1
                                        all_package.add(job1.package)
                                        grand_total_packages.append(job1.package)
                            else:
                                grand_total_applications += 1
                                print(app.student.University_Roll_Number, app.student.user.name)
                                if app.status == Application_status.SELECTED:
                                    selected1 += 1
                                    table_data2.append(
                                        [student_count, app.student.University_Roll_Number, app.student.user.name,
                                         app.student.branch, company1.company_name, app.Job_Drive.title,
                                         f'{app.Job_Drive.package} LPA'])
                                    student_count += 1
                                    all_package.add(job1.package)
                                    grand_total_packages.append(job1.package)
                    grand_total_job_drive += len(jds)
                    if len(jds) > 0:
                        table_data.append([count, company1.company_name, len(jds), selected1, f'{max(all_package) if len(all_package)>0 else 0} LPA'])
                        count += 1
            total_companies = len(table_data) - 1
            report_table = Table(table_data)
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Selected Students", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            report_table = Table(table_data2)
            report_table.setStyle(style)
            elements.append(report_table)
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceBefore=15, spaceAfter=15))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Summary", styles['Title']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph(f"Placement Percentage: {round(grand_total_selected*100/grand_total,2) if grand_total_selected > 0 and grand_total > 0 else 0} %", styles['Normal']))
            elements.append(Paragraph(f"Participating Companies: {total_companies}", styles['Normal']))
            elements.append(Paragraph(f"Total Job Drives: {grand_total_job_drive}", styles['Normal']))
            elements.append(Paragraph(f"Total Applications: {grand_total_applications}", styles['Normal']))
            elements.append(Paragraph(f"Students Selected: {grand_total_selected}", styles['Normal']))
            elements.append(Paragraph(f"Highest Package: {max(grand_total_packages) if len(grand_total_packages) > 0 else 0 } LPA", styles['Normal']))
            elements.append(Paragraph(f"Average Package: {round(sum(grand_total_packages)/len(grand_total_packages),2) if len(grand_total_packages) > 0 else 0} LPA", styles['Normal']))
            elements.append(Paragraph(f"Lowest Package: {min(grand_total_packages) if len(grand_total_packages) > 0 else 0} LPA", styles['Normal']))
            elements.append(Paragraph("<br/><br/>", styles['Normal']))
            elements.append(Paragraph("<para align='center'>Generated by Smart Placement Management System</para>",
                                      styles['Normal']))
            pdf.build(elements)
            buffer.seek(0)

            return send_file(
                buffer,
                mimetype="application/pdf",
                as_attachment=False,
                download_name="Student_Report.pdf"
            )


        Company_Name = [row.company_name for row in db.session.query(Companies.company_name).filter(Companies.creater_id == current_user.user_id).distinct().all()]
        Years = [r.graduation_year for r in Students.query.with_entities(Students.graduation_year).distinct().order_by(Students.graduation_year.desc()) if r.graduation_year is not None]
        branches = [row.branch for row in db.session.query(Students.branch).distinct().all() if row.branch is not None]
        return render_template("Placement_officer_Reports.html", report=report, Company_Name=Company_Name, branches=branches, Years = Years)

    elif report == 'Branch_wise_Report':
        pass
    elif report == 'Job_Drive_Report':
        pass
    elif report == 'Resume_Verification_Report':
        pass
    elif report == 'Interview_Repassport':
        pass
    elif report == 'Recruiter_Reports':
        pass
