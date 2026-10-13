# 🎓 Smart Placement Management System

A Flask-based web application for coordinating student placement activities across students, recruiters, and placement officers. 

## 🛑 Problem:

Colleges struggle to manage student profiles, resume verification, company drives, interview rounds, placement statistics, and recruiter feedback. Most colleges still depend on Excel sheets, WhatsApp groups, and emails. This makes it harder to maintain a consistent view of a student's placement progress.

## 💡 Solution:

Smart Placement Management System provides a shared web application with role-oriented interfaces where:

* 🧑‍🎓 **Students** can maintain profile information, browse job drives, apply, review application/interview information, and manage resume/certification-related files.
* 🏢 **Recruiters** can manage job drives, review applications, schedule interviews, and access candidate information.
* 💼 **Placement officers** can manage company information and placement drives, review students and interview information, and view analytics/reports.

## 🔄 Request flow

1. 🌐 A browser requests a route in app.py or one of the registered blueprints.
2. 🔀 Flask dispatches the request to the corresponding view function.
3. 🔒 Protected views use Flask-Login and role checks where implemented.
4. 🗄️ View functions query or update SQLAlchemy models.
5. 🖥️ The application renders a Jinja template, redirects the browser, serves a file, or returns generated report content.
6. ✉️ Some workflows call the notification module, which sends email through Brevo.

## ✨ Features

### 🔐 Authentication:
* Student, recruiter, and placement-officer login pages.
* User registration with duplicate-email and password-confirmation checks.
* Passwords stored using Werkzeug password hashing.
* Flask-Login session management and logout.
* Password-reset email flow using a time-limited signed token (one-hour maximum age).
* Role checks on role-specific dashboards and route handlers.

### 🧑‍🎓 Student workflows:
* Student dashboard which indicate profile completion, resume status, number of applications, number of Interviews, list of Upcoming Interviews, Applications, New job drive etc.
* Student Profile which shows personal, academic and professional information. 
* New Job-drive information
* Application details along with its status
* Interview information
* Resume/Certification upload and download route.

### 🏢 Recruiter workflows:
* Recruiter dashboard which shows Open job drives, Total applications, Shortlisted count, Selected count, information about Today’s interview.
* Job-drive creation, editing, deletion, listing.
* All Information about Applicant/application including their profile, resume, certification etc.
* Interview scheduling and interview tracking.

### 💼 Placement-officer workflows:
* Placement-officer dashboard which placement percentage, Unverified resumes count, Today’s Interview count, Active Job drives, list of Active Job drives, New Job drives
* Company creation, editing, and deletion, listing.
* New job drive information along with posting option where eligible students can be selected.
* Posted Job-drive along applicants information including their interview progress.
* Scheduled Interview information.
* Student details along with resume verification.
* Analytics page and report-generation route. The report route uses ReportLab components to create PDF output.

### 📢 Notifications:
The notifications.py module integrates with Brevo's transactional email client. 

* 📩 **To students**, it sends notification for registration, resume review, new placement opportunities, application status changes(shortlisted,Interview round cleared, selected, rejected) and interview events (scheduled, selected, rejected). 
* 📩 **To placement officer**, it sends notification when New job drive created by recruiter, Student applies for a job, Student opts out of a job drive, Student shortlisted, Student selected, Student rejected, Interview scheduled, Interview round cleared, Interview round rejected, Resume reuploaded.
* 📩 **To recruiter**, it sends notification when New applicants apply for job drives.

## 🛠️ Technology Stack

The **Smart Placement Management System** is built using Python, Flask, SQLAlchemy, and supporting libraries for authentication, database management, PDF report generation, and email notifications.

| 💻 Technology / Package | 📌 Version in Project | 🎯 Purpose |
|---|---|---|
| 🐍 **Python** | Not pinned | Core programming language used to develop and run the application. Uses `zoneinfo`, which is available in Python 3.9 and later. |
| 🌐 **Flask** | `3.1.3` | Web framework responsible for routing, request handling, templates, redirects, and flash messages. |
| 🎨 **Jinja2** | `3.1.6` | Server-side template engine used to render dynamic HTML pages. |
| 🔐 **Flask-Login** | `0.6.3` | Manages user login sessions and provides `current_user` and `login_required` functionality. |
| 🗄️ **Flask-SQLAlchemy** | `3.1.1` | Integrates SQLAlchemy with Flask for database models and session management. |
| 🔗 **SQLAlchemy** | `2.0.49` | ORM used for database access and interaction with application models. |
| 🐘 **psycopg2-binary** | `2.9.12` | PostgreSQL database driver, when PostgreSQL is used in the configured database URI. |
| 🛡️ **Werkzeug** | `3.1.8` | Provides password hashing and verification utilities, along with secure filename handling. |
| 🔑 **itsdangerous** | `2.2.0` | Supports signed, time-limited tokens used in the password-reset workflow. |
| ⚙️ **python-dotenv** | `1.2.3` | Loads environment variables from a `.env` file. |
| 📄 **ReportLab** | `5.0.0` | Generates PDF reports through the placement-officer functionality. |
| 🖼️ **Pillow** | `12.3.0` | Image-processing library dependency. Its exact runtime usage should be verified before removal. |
| 📧 **Brevo Python SDK** | Unpinned | Integrates with Brevo's transactional email API for application notifications. |
| 🚀 **Gunicorn** | `23.0.0` | WSGI server dependency intended for serving the Flask application. Deployment commands and container configuration are not included in the supplied project archive. |
| 🧩 **HTML, CSS & Jinja2 Templates** | Browser-provided / No separate package version | Build the server-rendered user interface, page layouts, and styling. The repository also includes Font Awesome and Material Design Iconic Font assets. |

