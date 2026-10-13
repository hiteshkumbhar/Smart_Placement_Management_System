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
