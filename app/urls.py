from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/update/', views.update_student_profile, name='update_student_profile'),
    path('hr/dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/post_job/', views.post_job, name='post_job'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('hr/contact/<int:application_id>/', views.contact_candidate, name='contact_candidate'),
    path('hr/schedule_interview/<int:application_id>/', views.schedule_interview, name='schedule_interview'),
    path('interview/update/<int:interview_id>/', views.update_interview_status, name='update_interview_status'),
]