import re
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from datetime import timedelta

from . import models as app_models
from .models import Profile, Student, Job, Application, Connection, Interview, Message, Notification, ResumeAnalysis
from .views import calculate_match_score, recommend_jobs_for_student, rank_applicants_for_job


class HRConnectPlatformTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.student_user = User.objects.create_user(username='student1', password='Pass1234')
        Profile.objects.create(user=self.student_user, role='student', phone_number='9999999999')
        self.student = Student.objects.create(
            user=self.student_user,
            degree='B.Tech',
            branch='CSE',
            college='Test University',
            passing_year=2024,
            skills='python,django',
            phone_number='9999999999',
            address='123 test street',
            date_of_birth='2000-01-01',
            gender='male',
            cgpa=9.1,
            linkedin_profile='https://linkedin.com/in/student1',
            github_profile='https://github.com/student1',
            preferred_location='City'
        )

        self.hr_user = User.objects.create_user(username='hr1', password='Pass1234')
        Profile.objects.create(user=self.hr_user, role='hr', company='Acme Corp', phone_number='8888888888')
        self.job = Job.objects.create(
            title='Django Developer',
            company='Acme Corp',
            skills_required='python,django,sql',
            education_required='B.Tech CSE',
            keywords='python,django',
            posted_by=self.hr_user
        )

    def test_student_registration_and_login_logout(self):
        register_url = reverse('register')
        data = {
            'username': 'newstudent',
            'password1': 'Newpass123',
            'password2': 'Newpass123',
            'role': 'student',
            'first_name': 'New',
            'last_name': 'Student',
            'email': 'new@student.com',
            'degree': 'B.Tech',
            'branch': 'CSE',
            'college': 'Test University',
            'passing_year': '2025',
            'skills': 'python,django',
            'phone_number': '7777777777',
            'address': '123 test',
            'date_of_birth': '2001-01-01',
            'gender': 'male',
            'cgpa': '8.5',
            'linkedin_profile': 'https://linkedin.com/in/newstudent',
            'github_profile': 'https://github.com/newstudent',
            'preferred_location': 'City',
        }
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newstudent').exists())

        login_url = reverse('login')
        response = self.client.post(login_url, {'username': 'newstudent', 'password': 'Newpass123'})
        self.assertEqual(response.status_code, 302)

        logout_url = reverse('logout')
        response = self.client.get(logout_url)
        self.assertEqual(response.status_code, 302)

    def test_hr_registration(self):
        register_url = reverse('register')
        data = {
            'username': 'newhr',
            'password1': 'Hrpass123',
            'password2': 'Hrpass123',
            'role': 'hr',
            'first_name': 'HR',
            'last_name': 'User',
            'email': 'hr@acme.com',
            'company': 'Acme Corp',
            'hr_phone': '5555555555',
        }
        response = self.client.post(register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Profile.objects.filter(user__username='newhr', role='hr').exists())

    def test_role_based_access_control(self):
        self.client.login(username='student1', password='Pass1234')
        response = self.client.get(reverse('hr_dashboard'))
        self.assertEqual(response.status_code, 302)

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_hr_can_post_job(self):
        self.client.login(username='hr1', password='Pass1234')
        response = self.client.post(reverse('post_job'), {
            'title': 'Frontend Engineer',
            'skills_required': 'html,css,javascript',
            'education_required': 'B.Tech CSE',
            'keywords': 'react,frontend'
        })
        self.assertRedirects(response, reverse('hr_dashboard'))
        self.assertTrue(Job.objects.filter(title='Frontend Engineer').exists())

    def test_student_job_application_and_unique_constraint(self):
        self.client.login(username='student1', password='Pass1234')

        apply_url = reverse('apply_job', args=[self.job.id])
        response = self.client.post(apply_url)
        self.assertRedirects(response, reverse('student_dashboard'))
        self.assertEqual(Application.objects.filter(student=self.student, job=self.job).count(), 1)

        response = self.client.post(apply_url)
        self.assertRedirects(response, reverse('student_dashboard'))
        self.assertEqual(Application.objects.filter(student=self.student, job=self.job).count(), 1)

    def test_application_status_transition_and_hr_view(self):
        self.client.login(username='student1', password='Pass1234')
        self.client.post(reverse('apply_job', args=[self.job.id]))
        app = Application.objects.get(student=self.student, job=self.job)
        self.assertEqual(app.status, Application.STATUS_APPLIED)

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')
        self.client.post(reverse('contact_candidate', args=[app.id]), {
            'contact_note': 'Fast tracking',
            'message': 'Let\'s schedule'
        })
        response = self.client.post(reverse('schedule_interview', args=[app.id]), {
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'mode': Interview.MODE_ONLINE,
            'notes': 'Please join 10 min early.'
        })
        self.assertRedirects(response, reverse('hr_dashboard'))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_INTERVIEW)

        response = self.client.get(reverse('hr_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django Developer')

    def test_hr_contact_candidate_creates_message_notification(self):
        self.client.login(username='student1', password='Pass1234')
        self.client.post(reverse('apply_job', args=[self.job.id]))
        app = Application.objects.get(student=self.student, job=self.job)

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')
        send = self.client.post(reverse('contact_candidate', args=[app.id]), {
            'contact_note': 'Can we connect?',
            'message': 'Please be ready for a call.'
        })
        self.assertRedirects(send, reverse('hr_dashboard'))

        connection = Connection.objects.get(application=app)
        self.assertTrue(connection.hr_contacted)
        self.assertTrue(Message.objects.filter(sender=self.hr_user, receiver=self.student_user, job=self.job).exists())
        self.assertTrue(Notification.objects.filter(user=self.student_user).exists())

    def test_interview_status_flow(self):
        self.client.login(username='student1', password='Pass1234')
        self.client.post(reverse('apply_job', args=[self.job.id]))
        app = Application.objects.get(student=self.student, job=self.job)
        self.client.logout()

        self.client.login(username='hr1', password='Pass1234')
        self.client.post(reverse('contact_candidate', args=[app.id]), {
            'contact_note': 'Fast tracking',
            'message': 'Let\'s schedule'
        })
        self.client.post(reverse('schedule_interview', args=[app.id]), {
            'scheduled_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'mode': Interview.MODE_OFFLINE,
            'notes': 'Bring your laptop.'
        })
        interview = Interview.objects.get(application=app)
        self.assertEqual(interview.status, Interview.STATUS_PENDING)

        self.client.logout()
        self.client.login(username='student1', password='Pass1234')
        update = self.client.post(reverse('update_interview_status', args=[interview.id]), {'status': Interview.STATUS_CONFIRMED})
        self.assertRedirects(update, reverse('home'), target_status_code=302)

        interview.refresh_from_db()
        self.assertEqual(interview.status, Interview.STATUS_CONFIRMED)
        self.assertTrue(Notification.objects.filter(user=self.student_user, message__contains='Interview status updated').exists())

    def test_resume_analysis_parsing_and_combined_skills(self):
        app_models.re = re
        resume_content = 'Python Django SQL React data'
        self.student.resume.save('resume.txt', ContentFile(resume_content), save=True)

        extracted = self.student.update_resume_skills()
        self.assertIn('python', extracted)
        self.assertIn('django', extracted)

        ra = ResumeAnalysis.objects.get(student=self.student)
        self.assertIn('python', ra.extracted_skills)
        self.assertIn('django', ra.extracted_skills)

        combined = self.student.combined_skills
        self.assertIn('python', combined)
        self.assertIn('django', combined)

    def test_ai_match_score_recommendation_and_ranking(self):
        second_student_user = User.objects.create_user(username='student2', password='Pass1234')
        Profile.objects.create(user=second_student_user, role='student')
        second_student = Student.objects.create(
            user=second_student_user,
            degree='B.Tech',
            branch='CSE',
            college='Other',
            passing_year=2024,
            skills='python,sql',
            phone_number='0000000000',
            address='',
            date_of_birth='2000-01-01',
            gender='male',
            cgpa=8.6,
            linkedin_profile='',
            github_profile='',
            preferred_location=''        
        )

        app1 = Application.objects.create(student=self.student, job=self.job, match_score=40)
        app2 = Application.objects.create(student=second_student, job=self.job, match_score=90)

        score = calculate_match_score(self.student, self.job)
        self.assertGreater(score, 0)

        recommended = recommend_jobs_for_student(self.student)
        self.assertTrue(len(recommended) >= 1)
        self.assertEqual(recommended[0]['job'].id, self.job.id)

        ranked = rank_applicants_for_job(self.job)
        self.assertEqual(ranked[0].student.user.username, 'student2')

    def test_hr_shortlist_and_result_flow(self):
        self.client.login(username='student1', password='Pass1234')
        self.client.post(reverse('apply_job', args=[self.job.id]))
        app = Application.objects.get(student=self.student, job=self.job)

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')

        self.client.post(reverse('shortlist_candidate', args=[app.id]))
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_SHORTLISTED)

        self.client.post(reverse('contact_candidate', args=[app.id]), {'message': 'Next round'})
        self.client.post(reverse('set_application_result', args=[app.id]), {'result': Application.STATUS_SELECTED})
        app.refresh_from_db()
        self.assertEqual(app.status, Application.STATUS_SELECTED)

    def test_mark_notifications_read(self):
        self.client.login(username='student1', password='Pass1234')
        self.client.post(reverse('apply_job', args=[self.job.id]))

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')
        app = Application.objects.get(student=self.student, job=self.job)
        self.client.post(reverse('contact_candidate', args=[app.id]), {'message': 'Hi'})

        self.client.logout()
        self.client.login(username='student1', password='Pass1234')
        unread_before = Notification.unread_count(self.student_user)
        self.assertGreater(unread_before, 0)
        self.client.get(reverse('mark_notifications_read'))
        unread_after = Notification.unread_count(self.student_user)
        self.assertEqual(unread_after, 0)

    def test_permission_and_edge_cases(self):
        self.client.login(username='student1', password='Pass1234')
        resp1 = self.client.post(reverse('contact_candidate', args=[999]), {'message': 'Test'})
        self.assertEqual(resp1.status_code, 404)

        resp2 = self.client.get(reverse('schedule_interview', args=[999]))
        self.assertEqual(resp2.status_code, 404)

        resp3 = self.client.post(reverse('apply_job', args=[999]))
        self.assertEqual(resp3.status_code, 404)

        hr_apply = self.client.login(username='hr1', password='Pass1234')
        resp_hr_apply = self.client.post(reverse('apply_job', args=[self.job.id]))
        self.assertRedirects(resp_hr_apply, reverse('home'), target_status_code=302)

        profile_only_user = User.objects.create_user(username='student_without_profile', password='Pass1234')
        Profile.objects.create(user=profile_only_user, role='student')
        self.client.logout()
        self.client.login(username='student_without_profile', password='Pass1234')
        response_redirect = self.client.get(reverse('student_dashboard'))
        self.assertRedirects(response_redirect, reverse('register'))

        self.client.logout()
        self.client.login(username='hr1', password='Pass1234')
        missing_app = Application.objects.create(student=self.student, job=self.job, match_score=50)
        del self.client

        # HR cannot update interview status for unrelated student when invalid interview_id
        self.client = Client()
        self.client.login(username='hr1', password='Pass1234')
        invalid = self.client.post(reverse('update_interview_status', args=[999]), {'status': Interview.STATUS_CONFIRMED})
        self.assertEqual(invalid.status_code, 404)
