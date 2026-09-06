from flask import render_template, request, redirect, flash, url_for, abort, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Users, Students, Companies, Job_Drives, Application_status, Applications, Interview_Rounds
import os
import datetime
from zoneinfo import ZoneInfo
from . import student_bp
from utils.notifications import notifications

@student_bp.route('/Student_Dashboard')
@login_required
def Student_Dashboard():
    if current_user.role != "student":
        abort(403)  # Forbidden

    student = Students.query.filter_by(user_id=current_user.user_id).first()

    ########################## Placement percentage ########################
    student_fields = [ 'branch', 'cgpa', 'skills', 'resume_path', 'graduation_year', 'profile_pic',
                    'mobile_number', 'Gender', 'DOB', 'Address', 'City', 'State', 'pin_code', 'University_Roll_Number',
                    'Semester', 'tenth_Percentage', 'Total_Backlogs', 'Active_Backlogs', 'LinkedIn', 'GitHub',
                    'Portfolio_Website', 'LeetCode', 'HackerRank', 'Certification']

    student_optional_fields = ['twelth_Percentage','Diploma_Percentage']
    filled_fields = 0
    total_fields = len(student_fields) + 1
    for field in student_fields:
        value = getattr(student, field, None)
        if value is not None and str(value).strip() != "":
            filled_fields += 1
            print(field)
    for field in student_optional_fields:
        value = getattr(student, field, None)
        if value is not None and str(value).strip() != "":
            filled_fields += 1
            break
    print('filled',filled_fields,'total',total_fields)
    percentage = round((filled_fields / total_fields) * 100)

    resume_status = student.resume_status

    total_applications = Applications.query.join(Job_Drives).filter(Applications.student_id == student.id,Applications.status.notin_([Application_status.REJECTED, Application_status.SELECTED]), Job_Drives.status != 'Closed').count()

    current_ist_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
    upcoming_interview_count = db.session.query(Interview_Rounds).join(Applications, Interview_Rounds.application_id == Applications.id).filter(Applications.student_id == student.id,Interview_Rounds.result.is_(None),Interview_Rounds.date > current_ist_time).count()

    selections = Applications.query.filter(Applications.student_id == student.id, Applications.status == Application_status.SELECTED).count()

    application_ids = db.session.scalars(db.select(Applications.id).where(Applications.student_id == student.id)).all()
    rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(application_ids),Interview_Rounds.result.is_(None),Interview_Rounds.date > current_ist_time).order_by(Interview_Rounds.date.asc()).limit(3).all()
    upcoming_interviews = []
    for r in rounds:
        upcoming_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name, r.date, r.link])

    application = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar(), Job_Drives.status != 'Closed').limit(3).all()
    applications = []
    for i in application:
        applications.append([db.session.query(Companies.company_name).filter(Companies.id == db.session.query(Job_Drives.company_id).filter(Job_Drives.id == i.drive_id).scalar()).scalar(),db.session.query(Job_Drives.title).filter(Job_Drives.id == i.drive_id).scalar(), i.status.value])

    if student.job_drive is not None:
        eligible_drives = [x.strip() for x in student.job_drive.split(',')]
        eligible_jobs = Job_Drives.query.filter(Job_Drives.id.in_(eligible_drives), Job_Drives.status == 'Active').limit(3).all()
    else:
        eligible_jobs = []
    job = []
    for i in eligible_jobs:
        job.append(
            [db.session.query(Companies.company_name).filter(Companies.id == i.company_id).scalar(), i.title,
             i.package, i.location, i.deadline])
    return render_template('Student_Dashboard.html', profile_percentage = percentage, resume_status = resume_status, total_applications = total_applications, upcoming_interview_count = upcoming_interview_count, selections = selections, upcoming_interviews = upcoming_interviews, applications = applications, job = job, student = student)


@student_bp.route('/Student_Application', methods = ['GET', 'POST'])
@login_required
def Application():
    if current_user.role != "student":
        abort(403)  # Forbidden

    total_applications = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id),Job_Drives.status != 'Closed').count()
    shortlisted_count = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(),Job_Drives.status != 'Closed',Applications.status == Application_status.SHORTLISTED).count()
    interview_count = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',Applications.status == Application_status.INTERVIEW).count()
    select_count = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',Applications.status == Application_status.SELECTED).count()
    reject_count = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',Applications.status == Application_status.REJECTED).count()

    filter = request.args.get('filter','All')
    if filter == 'shortlisted':
        application = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(),Job_Drives.status != 'Closed',Applications.status == Application_status.SHORTLISTED).all()
        applications = []
        for i in application:
            applications.append([i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value,i.drive_id, i.Job_Drive.company.logo_path])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Application.html', applications=applications, student=student, total_applications = total_applications, shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)
    elif filter == 'inteview':
        application = Applications.query.join(Job_Drives).filter(
            Applications.student_id == db.session.query(Students.id).filter(
                Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',
            Applications.status == Application_status.INTERVIEW).all()
        applications = []
        for i in application:
            applications.append(
                [i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value, i.drive_id, i.Job_Drive.company.logo_path])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Application.html', applications=applications, student=student, total_applications = total_applications,  shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)
    elif filter == 'selected':
        application = Applications.query.join(Job_Drives).filter(
            Applications.student_id == db.session.query(Students.id).filter(
                Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',
            Applications.status == Application_status.SELECTED).all()

        applications = []
        for i in application:
            applications.append(
                [i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value, i.drive_id, i.Job_Drive.company.logo_path])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Application.html', applications=applications, student=student, total_applications = total_applications,  shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)
    elif filter == 'rejected':
        application = Applications.query.join(Job_Drives).filter(
            Applications.student_id == db.session.query(Students.id).filter(
                Students.user_id == current_user.user_id).scalar_subquery(), Job_Drives.status != 'Closed',
            Applications.status == Application_status.REJECTED).all()
        applications = []
        for i in application:
            applications.append(
                [i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value, i.drive_id, i.Job_Drive.company.logo_path])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Application.html', applications=applications, student=student, total_applications = total_applications,  shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)

    if request.method == 'POST':
        search_term = f"%{request.form.get('search')}%"
        application = Applications.query.join(Job_Drives).join(Companies).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar_subquery(),Job_Drives.status != 'Closed',Companies.company_name.ilike(search_term)).all()
        applications = []
        for i in application:
            applications.append(
                [i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value, i.drive_id, i.Job_Drive.company.logo_path])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Application.html', applications=applications, student=student, total_applications = total_applications,  shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)

    application = Applications.query.join(Job_Drives).filter(Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id), Job_Drives.status != 'Closed').all()
    applications = []
    for i in application:
        applications.append([i.Job_Drive.company.company_name, i.Job_Drive.title, str(i.applied_at).split('.')[0], i.status.value, i.drive_id, i.Job_Drive.company.logo_path])
    student = Students.query.filter(Students.user_id == current_user.user_id).first()
    return render_template('Student_Application.html', applications = applications, student = student, total_applications = total_applications, shortlisted_count = shortlisted_count, interview_count = interview_count, select_count = select_count, reject_count = reject_count)


@student_bp.route('/Student_Application_Details')
@login_required
def Student_Application_Details():
    if current_user.role != "student":
        abort(403)  # Forbidden

    JD = Job_Drives.query.filter_by(id=request.args.get('job_id')).first()
    application = Applications.query.filter(Applications.drive_id == request.args.get('job_id'), Applications.student_id == db.session.query(Students.id).filter(Students.user_id == current_user.user_id).scalar()).first()
    Job = [JD, JD.company.company_name, application, application.Interview_Round]
    return render_template('Student_Application_Details.html',Job=Job)


@student_bp.route('/Student_interview', methods = ['GET', 'POST'])
@login_required
def Student_interview():
    if current_user.role != "student":
        abort(403)

    student = Students.query.filter_by(user_id = current_user.user_id).first()
    application_ids = db.session.scalars(db.select(Applications.id).where(Applications.student_id == student.id)).all()
    rounds = Interview_Rounds.query.filter(Interview_Rounds.application_id.in_(application_ids)).all()

    today_search = request.form.get('today_search')
    upcoming_search = request.form.get('upcoming_search')
    past_search = request.form.get('past_search')

    Todays_interview = []
    upcoming_interviews = []
    Past_interviews = []

    for r in rounds:
        if r.date.date() == datetime.date.today():
            if today_search:
                if today_search.lower() in r.Application.Job_Drive.company.company_name.lower():
                    Todays_interview.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path, r.id])
            else:
                Todays_interview.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path, r.id])
        elif r.date.date() > datetime.date.today():
            if upcoming_search:
                if upcoming_search.lower() in r.Application.Job_Drive.company.company_name.lower():
                    upcoming_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name,r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path, r.id])
            else:
                upcoming_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path, r.id])
        else:
            if past_search:
                if past_search.lower() in r.Application.Job_Drive.company.company_name.lower():
                    Past_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name,r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path. r.id])
            else:
                Past_interviews.append([r.Application.Job_Drive.company.company_name, r.Application.Job_Drive.title, r.round_name, r.date, r.link, r.result, r.feedback, r.Application.Job_Drive.company.logo_path, r.id])

    student = Students.query.filter(Students.user_id == current_user.user_id).first()
    return render_template('Student_interview.html', Todays_interview = Todays_interview, upcoming_interviews = upcoming_interviews, Past_interviews = Past_interviews, student = student)


@student_bp.route('/Student_Job_Drive', methods = ['GET','POST'])
@login_required
def Student_Job_Drive():
    if current_user.role != "student":
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

        Student = Students.query.filter_by(user_id=current_user.user_id).first()
        if Student.job_drive is not None:
            eligible_drives = [x.strip() for x in Student.job_drive.split(',')]
            eligible_jobs = Job_Drives.query.filter(Job_Drives.id.in_(eligible_drives),Job_Drives.status == 'Expired').all()
        else:
            eligible_jobs = []
        job = []

        for i in eligible_jobs:
            job.append(
                [i.id, db.session.query(Companies.company_name).filter(Companies.id == i.company_id).scalar(), i.title,
                 i.package, i.location, i.deadline, i.description,i.status])
        student = Students.query.filter(Students.user_id == current_user.user_id).first()

        return render_template('Student_Job_Drive.html', job=job, student = student)

    if request.method == 'POST':

        job_id = request.args.get('id')
        job1 = Job_Drives.query.filter(Job_Drives.id == job_id).first()
        action = request.form.get("action")
        if action == 'apply':
            Student = Students.query.filter_by(user_id=current_user.user_id).first()
            if Student.resume_status == 'Verified':
                if Applications.query.filter_by(student_id = Student.id, drive_id = job_id).first():
                    flash('Already applied for this role','Duplicate_Application_Error')
                    return redirect(url_for('student.Student_Job_Drive'))
                eligible_drives = [x.strip() for x in Student.job_drive.split(',')]
                eligible_drives.remove(job_id)
                if len(eligible_drives) == 0:
                    Student.job_drive = None
                else:
                    Student.job_drive = ','.join(eligible_drives)

                application = Applications(student_id = Student.id, drive_id = job_id, status = 'APPLIED')
                db.session.add(application)

                app_count = job1.application_count_email.copy()                   # IMPORTANT: SQLAlchemy does not automatically track in-place changes to JSON columns. You must make a copy, modify it, and reassign it to the record.
                app_count["email_count"] += 1
                app_count["student_id"].append(Student.id)
                if app_count["email_count"] == 5:
                    recruiter = Users.query.filter(Users.user_id == job1.creater_id).first()
                    student_list = []
                    for s1 in app_count["student_id"]:
                        student1 = Students.query.filter(Students.id == s1).first()
                        student_list.append([student1.user.name, student1.branch, student1.cgpa])
                    notifications(['Student_applied_Recruiter', recruiter.email, student_list, job1.title, job1.company.company_name])
                    app_count["email_count"] = 0
                job1.application_count_email = app_count

                db.session.commit()
                notifications(['Student_applied_Placement_officer', [user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], Student.user.name, job1, job1.company.company_name])
            else:
                flash('Please wait until your resume is verified.', 'Resume_verification_Error')
        elif action == 'opt_out':

            Student = Students.query.filter_by(user_id=current_user.user_id).first()
            if Applications.query.filter_by(student_id=Student.id, drive_id=job_id).first():
                flash('Application is already in process', 'Duplicate_Application_Error')
                return redirect(url_for('student.Student_Job_Drive'))
            eligible_drives = [x.strip() for x in Student.job_drive.split(',')]
            eligible_drives.remove(job_id)
            if len(eligible_drives) == 0:
                Student.job_drive = None
            else:
                Student.job_drive = ','.join(eligible_drives)

            job = Job_Drives.query.filter_by(id = job_id).first()
            if job.opt_out is None:
                job.opt_out = Student.id
            else:
                job.opt_out = job.opt_out + ',' + str(Student.id)

            db.session.commit()
            notifications(['Student_opted_out_Placement_officer',[user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()],Student.user.name, job1, job1.company.company_name])

        Student = Students.query.filter_by(user_id=current_user.user_id).first()
        if Student.job_drive is not None:
            eligible_drives = [int(x.strip()) for x in Student.job_drive.split(',')]
            eligible_jobs = Job_Drives.query.filter(Job_Drives.id.in_(eligible_drives), Job_Drives.status == 'Active').all()
        else:
            eligible_jobs = []
        job = []

        for i in eligible_jobs:
            job.append(
                [i.id, db.session.query(Companies.company_name).filter(Companies.id == i.company_id).scalar(), i.title,
                 i.package, i.location, i.deadline, i.description,i.status])

        student = Students.query.filter(Students.user_id == current_user.user_id).first()
        return render_template('Student_Job_Drive.html', job=job, job_id = job_id, student = student)

    Student = Students.query.filter_by(user_id=current_user.user_id).first()
    if Student.job_drive is not None:
        eligible_drives = [x.strip() for x in Student.job_drive.split(',')]
        eligible_jobs = Job_Drives.query.filter(Job_Drives.id.in_(eligible_drives),Job_Drives.status == 'Active').all()
    else:
        eligible_jobs = []
    job = []

    for i in eligible_jobs:
        job.append([i.id, i.company.company_name, i.title, i.package, i.location, i.deadline, i.description,i.status, i.company.logo_path])

    student = Students.query.filter(Students.user_id == current_user.user_id).first()
    return render_template('Student_Job_Drive.html', job = job, student = student)


@student_bp.route('/Student_Profile', methods=['GET', 'POST'])
@login_required
def Student_Profile():
    if current_user.role != "student":
        abort(403)  # Forbidden

    student = Students.query.filter_by(user_id=current_user.user_id).first()

    if request.args.get('Download') and request.args.get('Download') == 'download_resume':
        RESUME_FOLDER = os.path.join(current_app.root_path, "static", "Docs", "student", "resumes")
        if not student.resume_path:
            abort(404)
        filename = secure_filename(student.resume_path)
        return send_from_directory(
            directory=RESUME_FOLDER,
            path=filename,
            as_attachment=True,
            download_name=student.resume_path
        )

    mode = request.args.get('mode', 'View')

    if request.method == 'POST':
        if request.form.get('action') == 'go_to_update':
            return redirect(url_for('student.Student_Profile', mode='Update'))
        if request.form.get('action') == 'change_photo':
            MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
            profile_photo = request.files.get('profile_photo')
            if profile_photo and profile_photo.filename != '':
                profile_photo.seek(0, os.SEEK_END)
                file_size = profile_photo.tell()
                profile_photo.seek(0)

                if file_size > MAX_FILE_SIZE_BYTES:
                    flash('File size must be less that 5 mb', 'profile_photo_size_error')
                    return redirect(url_for('student.Student_Profile', mode='View'))

                file_extension = profile_photo.filename.rsplit('.', 1)[1].lower()
                if file_extension not in ['jpg', 'jpeg', 'png']:
                    flash('Upload file in jpg or jpeg or png format', 'profile_photo_extension_error')
                    return redirect(url_for('student.Student_Profile', mode='View'))

                FOLDER = os.path.join('static', 'Images', 'student', 'profile_photo')
                os.makedirs(FOLDER, exist_ok=True)

                safe_name = secure_filename(current_user.name)
                filename = f"User_{current_user.user_id}_{safe_name}.{file_extension}"
                filepath = os.path.join(FOLDER, filename)
                profile_photo.save(filepath)

                student.profile_pic = filename
                db.session.commit()
                return redirect(url_for('student.Student_Profile', mode='View'))

        MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
        resume_file = request.files.get('resume_file')
        if resume_file and resume_file.filename != '':
            resume_file.seek(0, os.SEEK_END)
            file_size = resume_file.tell()
            resume_file.seek(0)
            resume_extension = resume_file.filename.rsplit('.', 1)[-1].lower()

            if resume_extension == 'pdf' and file_size < MAX_FILE_SIZE_BYTES:
                RESUME_FOLDER = os.path.join('static', 'Docs', 'student', 'resumes')
                os.makedirs(RESUME_FOLDER, exist_ok=True)

                safe_name = secure_filename(current_user.name)
                resume_filename = f"Resume_{current_user.user_id}_{safe_name}.pdf"
                resume_file.save(os.path.join(RESUME_FOLDER, resume_filename))
                if student.resume_path is None:
                    student.resume_path = resume_filename
                else:
                    student.resume_status = 'Reuploaded'
                    student.resume_path = resume_filename
                    notifications(['Student_resume_reuploaded', [user.email for user in Users.query.filter(Users.role == 'Placement_Officer').all()], student.user.name])
            else:
                if resume_extension != 'pdf':
                    flash('Upload resume strictly in PDF format', 'resume_extention_error')
                if file_size > MAX_FILE_SIZE_BYTES:
                    flash('Resume file size must be less that 5 mb', 'Resume_file_size_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))

        certification = request.files.get('Certification')
        if certification and certification.filename != '':
            certification.seek(0, os.SEEK_END)
            certification_file_size = certification.tell()
            certification.seek(0)
            certification_extension = certification.filename.rsplit('.', 1)[-1].lower()
            if certification_extension == 'pdf' and certification_file_size < MAX_FILE_SIZE_BYTES:
                CERT_FOLDER = os.path.join('static', 'Docs', 'student', 'certifications')
                os.makedirs(CERT_FOLDER, exist_ok=True)
                safe_name = secure_filename(current_user.name)
                certification_filename = f"Cert_{current_user.user_id}_{safe_name}_{secure_filename(certification.filename)}"
                certification.save(os.path.join(CERT_FOLDER, certification_filename))
                if not student.Certification:
                    student.Certification = certification.filename
                else:
                    student.Certification = student.Certification + ', ' + certification.filename
            else:
                if certification_extension != 'pdf':
                    flash('Upload Certification strictly in PDF format', 'Certification_extention_error')
                if certification_file_size > MAX_FILE_SIZE_BYTES:
                    flash('Certification file size must be less that 5 mb', 'Certification_file_size_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))

        if request.form.get('branch'):
            student.branch = request.form.get('branch')
        if request.form.get('cgpa'):
            student.cgpa = request.form.get('cgpa')
        if request.form.get('skills'):
            student.skills = request.form.get('skills')
        if request.form.get('graduation_year'):
            student.graduation_year = request.form.get('graduation_year')
        if request.form.get('name'):
            current_user.name = request.form.get('name')
        if request.form.get('mobile_number'):
            if request.form.get('mobile_number') != db.session.query(Students.mobile_number).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('mobile_number') in db.session.scalars(db.select(Students.mobile_number)).all():
                flash('This mobile number is already taken!', 'mobile_number_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.mobile_number = request.form.get('mobile_number')
        if request.form.get('Gender'):
            student.Gender = request.form.get('Gender')
        if request.form.get('DOB'):
            student.DOB = request.form.get('DOB')
        if request.form.get('Address'):
            student.Address = request.form.get('Address')
        if request.form.get('City'):
            student.City = request.form.get('City')
        if request.form.get('State'):
            student.State = request.form.get('State')
        if request.form.get('pin_code'):
            student.pin_code = request.form.get('pin_code')
        if request.form.get('University_Roll_Number'):
            if request.form.get('University_Roll_Number') != db.session.query(Students.University_Roll_Number).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('University_Roll_Number') in db.session.scalars(db.select(Students.University_Roll_Number)).all():
                flash('This roll number is already taken!', 'roll_number_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.University_Roll_Number = request.form.get('University_Roll_Number')
        if request.form.get('Semester'):
            student.Semester = request.form.get('Semester')
        if request.form.get('tenth_Percentage'):
            student.tenth_Percentage = request.form.get('tenth_Percentage')
        if request.form.get('twelth_Percentage'):
            student.twelth_Percentage = request.form.get('twelth_Percentage')
        if request.form.get('Diploma_Percentage'):
            student.Diploma_Percentage = request.form.get('Diploma_Percentage')
        if request.form.get('Total_Backlogs'):
            student.Total_Backlogs = request.form.get('Total_Backlogs')
        if request.form.get('Active_Backlogs'):
            student.Active_Backlogs = request.form.get('Active_Backlogs')
        student.updated_at = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        if request.form.get('LinkedIn'):
            if request.form.get('LinkedIn') != db.session.query(Students.LinkedIn).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('LinkedIn') in db.session.scalars(db.select(Students.LinkedIn)).all():
                flash('This LinkedIn website is already taken!', 'LinkedIn_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.LinkedIn = request.form.get('LinkedIn')
        if request.form.get('GitHub'):
            if request.form.get('GitHub') != db.session.query(Students.GitHub).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('GitHub') in db.session.scalars(db.select(Students.GitHub)).all():
                flash('This GitHub website is already taken!', 'GitHub_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.GitHub = request.form.get('GitHub')
        if request.form.get('Portfolio_Website'):
            if request.form.get('Portfolio_Website') != db.session.query(Students.Portfolio_Website).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('Portfolio_Website') in db.session.scalars(db.select(Students.Portfolio_Website)).all():
                flash('This Portfolio website is already taken!', 'Portfolio_Website_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.Portfolio_Website = request.form.get('Portfolio_Website')
        if request.form.get('LeetCode'):
            if request.form.get('LeetCode') != db.session.query(Students.LeetCode).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('LeetCode') in db.session.scalars(db.select(Students.LeetCode)).all():
                flash('This LeetCode website is already taken!', 'LeetCode_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.LeetCode = request.form.get('LeetCode')
        if request.form.get('HackerRank'):
            if request.form.get('HackerRank') != db.session.query(Students.HackerRank).filter(Students.user_id == current_user.user_id).scalar() and request.form.get('HackerRank') in db.session.scalars(db.select(Students.HackerRank)).all():
                flash('This HackerRank website is already taken!', 'HackerRank_error')
                return redirect(url_for('student.Student_Profile', mode='Update'))
            student.HackerRank = request.form.get('HackerRank')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.Student_Profile', mode='View'))


    return render_template('Student_Profile.html', student = student, name=current_user.name, mode=mode)


@student_bp.route("/student/certification/download", methods = ['GET','POST'])
@login_required
def student_download_certifications():
    if current_user.role != "student":
        abort(403)  # Forbidden
    name = request.form.get('name')
    print(name)
    filename = f"Cert_{request.form.get('id')}_{db.session.query(Users.name).filter(Users.user_id == request.form.get('id')).scalar()}_{name.strip()}"
    RESUME_FOLDER = os.path.join(current_app.root_path, "static", "Docs", "student", "certifications")
    return send_from_directory(directory=RESUME_FOLDER, path=secure_filename(filename), as_attachment=True, download_name=name)
