import os
from flask import current_app, render_template_string
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import datetime

from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)
def send_email(to_email, subject, html_content):

    api_key = os.getenv("BREVO_API_KEY")

    client = Brevo(api_key=api_key)

    try:

        response = client.transactional_emails.send_transac_email(
            subject=subject,

            html_content=html_content,

            sender=SendTransacEmailRequestSender(
                name="Smart Placement Management",
                email="smartplacement2026@gmail.com"
            ),

            to=[
                SendTransacEmailRequestToItem(
                    email=to_email
                )
            ]
        )

        current_app.logger.info(
            "Email sent successfully: %s",
            response.message_id
        )

        return True

    except Exception as e:

        current_app.logger.error(
            "Email sending failed: %r",
            e
        )

        return False


def notifications(mode):
    if mode[0] == 'Registration':
        name = mode[1]
        email = mode[2]
        html_message= f"""
        Hello {name},

        Your account has been created successfully.

        {'You can now login and complete your profile.' if mode[3] == 'student' else 'You can now login to your account'}

        Regards,
        Placement Cell"""
        return send_email(
            email,
            'Welcome to Smart Placement Management System',
            html_message
        )


    elif mode[0] == 'resumeverified':
        email = mode[1]
        html_message = f"""
        Congratulations!

        Your resume has been verified.

        You are now eligible to apply for placement drives."""
        return send_email(
            email,
            'Resume Verified',
            html_message
        )

    elif mode[0] == 'resumerejected':
        email = mode[1]
        html_message = f"""
        Your resume has been rejected.

        {f'Reason: {mode[2]}' if mode[2] is not None else ''}

        Please upload a corrected resume.
        """
        return send_email(
            email,
            'Resume Requires Changes',
            html_message
        )

    elif mode[0] == 'Postjobdrive':
        email = mode[1]
        html_message = f"""
        Dear Student, 
        Details of new job opportunity is given below. 

        Company:{mode[2]}
        Role:{mode[3]}
        Package: {mode[4]} LPA
        Deadline: {mode[5].strftime("%d-%m-%Y")}
        name
        Login to apply.
        """
        return send_email(
            email,
            'New Placement Opportunity',
            html_message
        )

    elif mode[0] == 'shortlisted':
        email = mode[1]
        html_message = f"""
        Congratulations!

        You have been shortlisted for the role of {mode[3]} in {mode[2]}.            
        """
        return send_email(
            email,
            'Shortlisted',
            html_message
        )

    elif mode[0] == 'Schedule_interview':
        email = mode[1]
        date_obj = datetime.datetime.strptime(mode[5], "%Y-%m-%dT%H:%M")
        html_message = f"""
        Dear student,
        Details of scheduled interview is given below:

        Company : {mode[2]}
        Role : {mode[3]}
        Round name : {mode[4]}
        Date : {date_obj.strftime("%d-%m-%Y")}
        Time : {date_obj.strftime("%I:%M %p")}

        Login to get link.
        """
        return send_email(
            email,
            'Interview scheduled',
            html_message
        )

    elif mode[0] == 'selected':
        email = mode[1]
        html_message= f"""
        Congratulations!

        You are selected for {mode[3]} role in {mode[2]}.
"""
        return send_email(
            email,
            'Selected',
            html_message
        )

    elif mode[0] == 'rejected':
        email = mode[1]
        html_message = f"""
        Thank you for participating.

        Unfortunately, you are not selected for {mode[3]} role in {mode[2]}.
        """
        return send_email(
            email,
            'Rejected',
            html_message
        )

    elif mode[0] == 'Cleared':
        email = mode[1]
        html_message = f"""
        Congratulations!

        You have cleared {mode[4]} {'round' if 'round' not in mode[4].lower() else ''} of {mode[3]} role in {mode[2]}.
        """
        return send_email(
            email,
            'Interview round Cleared',
            html_message
        )

    elif mode[0] == 'recruiter_job_drive_create':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            New Job Drive details are given below:

            Company name: {mode[3]}
            Role: {mode[2].title}
            Package: {mode[2].package}
            Location: {mode[2].location}
            Vacancies: {mode[2].Vacancies}
            Deadline: {mode[2].deadline.strftime("%d-%m-%Y %I:%M %p")}

            Login to post this Job Drive.
            """

            send_email(
                email,
                'New Job Drive',
                html_message
            )

        return True
    elif mode[0] == 'Student_applied_Placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            {mode[2]} has applied for {mode[3].title} role in {mode[4]}.
            """
            send_email(
                email,
                'Student applied',
                html_message
            )
        return True


    elif mode[0] == 'Student_opted_out_Placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,
                
            {mode[2]} has opted out from {mode[3].title} role in {mode[4]}.
            """
            send_email(
                email,
                'Student Opted out',
                html_message
            )
        return True

    elif mode[0] == 'student_shortlisted_placement_officer':
        emails = mode[1]
        for email in emails:
            html_message= f"""
            Dear Placement officer,

            {mode[2]} is shortlisted for the role of {mode[4]} in {mode[3]}.
            """
            send_email(
                email,
                'Student shortlisted',
                html_message
            )
        return True

    elif mode[0] == 'student_selected_placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            Congratulations!

            {mode[2]} is selected for the role of {mode[4]} in {mode[3]}.
            """
            send_email(
                email,
                'Selected',
                html_message
            )
        return True

    elif mode[0] == 'student_rejected_placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,
            {mode[2]} is rejected for the role of {mode[4]} in {mode[3]}.
            """
            send_email(
                email,
                'Rejected',
                html_message
            )
        return True

    elif mode[0] == 'student_interview_scheduled_placement_officer':
        emails = mode[1]
        date_obj = datetime.datetime.strptime(mode[6], "%Y-%m-%dT%H:%M")
        for email in emails:
            html_message = f"""
            Dear Placement officer,
            Details of the scheduled interview are given below:

            Student name: {mode[2]}
            Comapny: {mode[3]}
            Role: {mode[4]}
            Round Name: {mode[5]}
            Interview Date and time: {date_obj.strftime("%d-%m-%Y %I:%M %p")}
            """
            send_email(
                email,
                'Interview scheduled',
                html_message
            )
        return True

    elif mode[0] == 'student_cleared_placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            {mode[2]} has cleared {mode[5]} {'round' if 'round' not in mode[5].lower() else ''} of {mode[4]} role in {mode[3]}
            """
            send_email(
                email,
                'Interview round cleared',
                html_message
            )
        return True

    elif mode[0] == 'student_rejected_round_placement_officer':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            {mode[2]} is rejected in {mode[5]} {'round' if 'round' not in mode[5].lower() else ''} of {mode[4]} role in {mode[3]}
            """
            send_email(
                email,
                'Rejected',
                html_message
            )
        return True

    elif mode[0] == 'Student_resume_reuploaded':
        emails = mode[1]
        for email in emails:
            html_message = f"""
            Dear Placement officer,

            {mode[2]} has reuploaded updated resume. Kindly verify.
            """
            send_email(
                email,
                'Resume reuploaded',
                html_message
            )
        return True

    elif mode[0] == 'Student_applied_Recruiter':
        email = mode[1]
        email_html_template = """
                5 New Applicants have applied for {{ mode[3] }} role in {{ mode[4] }}. Details of these applicants are given below.

                <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border: 1px solid black; font-family: Arial, sans-serif;">
                <tr>
                <th style="border: 1px solid black; background-color: #f2f2f2; text-align: left;">Student Name</th>
                <th style="border: 1px solid black; background-color: #f2f2f2; text-align: left;">Branch</th>
                <th style="border: 1px solid black; background-color: #f2f2f2; text-align: left;">CGPA</th>
                </tr>
                {% for student in students %}
                <tr>
                <td style="border: 1px solid black;">{{student[0]}}</td>
                <td style="border: 1px solid black;">{{student[1]}}</td>
                <td style="border: 1px solid black;">{{student[2]}}</td>
                </tr>
                {% endfor %}
                </table>
                """
        final_email_html = render_template_string(
            email_html_template,
            students=mode[2],
            mode=mode
        )

        send_email(
            email,
            '5 New Applicants',
            final_email_html
        )
    return True