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
| 💻 Technology / Package | 🎯 Purpose |
|---|---|
| 🐍 **Python** |  Main programming language. The code uses standard-library features including `zoneinfo`. |
| 🌐 **Flask** | Web framework for routes, request handling, blueprints, redirects, flash messages, and responses. |
| 🧩 **Flask-JWT-Extended** | Creates and validates access/refresh JWTs and supports JWT authentication in headers and cookies. |
| 🗄️ **Flask-SQLAlchemy** | Connects Flask to SQLAlchemy models and database sessions. |
| 🔗 **SQLAlchemy** | ORM and query layer for users, student profiles, companies, job drives, applications, and interview rounds. |
| 🐘 **psycopg2-binary** | PostgreSQL driver when the configured `SQLALCHEMY_DATABASE_URI` uses PostgreSQL. The database URI is supplied through environment configuration. |
| 🛡️ **Werkzeug** | Password hashing and verification, secure filename handling, and Flask's underlying WSGI utilities. |
| 🎨 **Jinja2** | Server-side HTML templating for dynamic pages in `templates/`. |
| 🧾 **HTML, CSS and JavaScript** | User interface built from HTML templates and CSS. No separate frontend framework or JavaScript package manager manifest is present in the archive. |
| 🔤 **Font Awesome** | Icon font and CSS assets used by the interface. |
| 🔣 **Material Design Iconic Font** | Additional icon font assets used by the interface. |
| 🔠 **Poppins** | Typography assets included in the repository. |
| ⚙️ **python-dotenv** | Loads environment variables from a `.env` file. |
| 🔑 **itsdangerous** | Supports signed, time-limited tokens used in password-reset functionality. |
| 📄 **ReportLab** | Generates PDF reports for placement-officer reporting. |
| 📧 **Brevo Python SDK** (`brevo-python`) | Sends transactional email notifications through Brevo. |
| 🚀 **Gunicorn** | WSGI HTTP server dependency for running the Flask application in a deployment environment. |
| 🧪 **pytest** | Test framework used by the tests under `tests/` and the project test configuration. |

