from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Profile, Student, Job, Application, Connection, Interview, Message, Notification, ResumeAnalysis
from .forms import StudentForm, JobForm
import re

def calculate_match_score(student, job):
    # Skill matching (50%)
    student_skills = set(s.strip().lower() for s in student.skills.split(','))
    job_skills = set(s.strip().lower() for s in job.skills_required.split(','))
    if job_skills:
        skill_match = len(student_skills & job_skills) / len(job_skills) * 100
    else:
        skill_match = 0

    # Resume keyword matching (30%)
    resume_text = student.get_resume_text()
    job_keywords = set(k.strip().lower() for k in job.keywords.split(',')) if job.keywords else set()
    if job_keywords:
        keyword_count = sum(1 for kw in job_keywords if kw in resume_text)
        resume_match = keyword_count / len(job_keywords) * 100
    else:
        resume_match = 0

    # Education matching (20%)
    education_match = 0
    if student.degree.lower() in job.education_required.lower() and student.branch.lower() in job.education_required.lower():
        education_match = 100

    match_score = 0.5 * skill_match + 0.3 * resume_match + 0.2 * education_match
    return round(match_score, 2)

def get_match_label(score):
    if score > 70:
        return "Highly Relevant"
    elif score >= 40:
        return "Moderate Match"
    else:
        return "Low Match"

# Recommendation engine
def recommend_jobs_for_student(student, top_n=5):
    jobs = Job.objects.all()
    scored = []
    for job in jobs:
        score = calculate_match_score(student, job)
        if score > 0:
            scored.append((job, score))
    scored.sort(key=lambda kv: kv[1], reverse=True)
    return [{'job': job, 'score': score, 'label': get_match_label(score)} for job, score in scored[:top_n]]

# HR candidate ranking for each job
def rank_applicants_for_job(job):
    applications = list(Application.objects.filter(job=job).select_related('student__user'))
    def candidate_value(app):
        student = app.student
        strength = 0
        if student.skills:
            strength += 20
        if student.resume:
            strength += 20
        if student.cgpa:
            strength += 10
        if student.degree and student.branch and student.college:
            strength += 15
        if student.linkedin_profile:
            strength += 5
        if student.github_profile:
            strength += 5
        if student.preferred_location:
            strength += 5
        return app.match_score * 0.6 + strength * 0.4

    applications.sort(key=candidate_value, reverse=True)
    return applications


def home(request):
    if request.user.is_authenticated:
        try:
            profile = Profile.objects.get(user=request.user)
            if profile.role == 'student':
                return redirect('student_dashboard')
            else:
                return redirect('hr_dashboard')
        except Profile.DoesNotExist:
            return redirect('register')
    return render(request, 'home.html')

def register(request):
    form_data = {}
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        role = request.POST.get('role')
        form_data = request.POST.dict()

        if form.is_valid():
            try:
                user = form.save()
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = request.POST.get('email', '')
                user.save()
                Profile.objects.create(user=user, role=role, company=request.POST.get('company', ''), phone_number=request.POST.get('hr_phone', ''))
                if role == 'student':
                    passing_year_str = request.POST.get('passing_year', '0')
                    try:
                        passing_year = int(passing_year_str) if passing_year_str else 0
                    except ValueError:
                        passing_year = 0
                    Student.objects.create(
                        user=user,
                        degree=request.POST.get('degree', ''),
                        branch=request.POST.get('branch', ''),
                        college=request.POST.get('college', ''),
                        passing_year=passing_year,
                        skills=request.POST.get('skills', ''),
                        phone_number=request.POST.get('phone_number', ''),
                        address=request.POST.get('address', ''),
                        date_of_birth=request.POST.get('date_of_birth') or None,
                        gender=request.POST.get('gender', ''),
                        cgpa=request.POST.get('cgpa') or None,
                        linkedin_profile=request.POST.get('linkedin_profile', ''),
                        github_profile=request.POST.get('github_profile', ''),
                        preferred_location=request.POST.get('preferred_location', '')
                    )
                messages.success(request, 'Registration successful!')
                login(request, user)
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Error during registration: {str(e)}')
        else:
            messages.error(request, 'Form is invalid. Please check the fields.')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form, 'form_data': form_data})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('register')

    jobs = Job.objects.all()
    matched_jobs = []
    for job in jobs:
        score = calculate_match_score(student, job)
        if score > 0:  # or show all
            matched_jobs.append({
                'job': job,
                'score': score,
                'label': get_match_label(score)
            })
    matched_jobs.sort(key=lambda x: x['score'], reverse=True)

    # Extract skills from resume if needed
    student.update_resume_skills()

    # Profile strength
    strength = 0
    if student.skills:
        strength += 20
    if student.resume:
        strength += 20
    if student.degree and student.branch and student.college:
        strength += 15
    if student.phone_number:
        strength += 5
    if student.address:
        strength += 5
    if student.date_of_birth:
        strength += 5
    if student.gender:
        strength += 5
    if student.cgpa:
        strength += 10
    if student.linkedin_profile:
        strength += 5
    if student.github_profile:
        strength += 5
    if student.preferred_location:
        strength += 5
    profile_strength = min(strength, 100)

    # Current applications for tracking
    applications = Application.objects.filter(student=student).select_related('job').order_by('-applied_at')
    interviews = Interview.objects.filter(application__student=student).select_related('application__job')
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    messages_list = Message.objects.filter(receiver=request.user).order_by('-created_at')[:20]

    # recommendations
    recommended_jobs = recommend_jobs_for_student(student, top_n=6)
    unread_notifications = Notification.unread_count(request.user)

    return render(request, 'student_dashboard.html', {
        'student': student,
        'matched_jobs': matched_jobs,
        'profile_strength': profile_strength,
        'applications': applications,
        'interviews': interviews,
        'notifications': notifications,
        'inbox_messages': messages_list,
        'recommended_jobs': recommended_jobs,
        'unread_notifications_count': unread_notifications,
    })

@login_required
def hr_dashboard(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'hr':
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('register')

    jobs = Job.objects.filter(posted_by=request.user)
    job_applications = []
    for job in jobs:
        apps = rank_applicants_for_job(job)
        shortlisted = [a for a in apps if a.status == Application.STATUS_SHORTLISTED]
        contacted = [a for a in apps if a.contacted_at]
        job_applications.append({
            'job': job,
            'applications': apps,
            'shortlisted': shortlisted,
            'contacted': contacted,
            'ranked': apps,
        })

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    messages_list = Message.objects.filter(receiver=request.user).order_by('-created_at')[:20]
    unread_notifications = Notification.unread_count(request.user)

    return render(request, 'hr_dashboard.html', {
        'job_applications': job_applications,
        'notifications': notifications,
        'inbox_messages': messages_list,
        'unread_notifications_count': unread_notifications,
    })

@login_required
def post_job(request):
    try:
        profile = Profile.objects.get(user=request.user)
        if profile.role != 'hr':
            return redirect('home')
    except Profile.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.company = profile.company
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('hr_dashboard')
        else:
            messages.error(request, 'Form is invalid. Please check the fields.')
    else:
        form = JobForm()
    return render(request, 'post_job.html', {'form': form})

@login_required
def update_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('student_dashboard')
        else:
            messages.error(request, 'Form is invalid. Please check the fields.')
    else:
        form = StudentForm(instance=student)
    return render(request, 'update_student_profile.html', {'form': form})

@login_required
def apply_job(request, job_id):
    profile = Profile.objects.get(user=request.user)
    if profile.role != 'student':
        messages.error(request, 'Only students can apply to jobs.')
        return redirect('home')

    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('register')

    job = get_object_or_404(Job, id=job_id)

    if request.method == 'GET':
        already_applied = Application.objects.filter(student=student, job=job).exists()
        return render(request, 'apply_job.html', {
            'job': job,
            'already_applied': already_applied,
        })

    if Application.objects.filter(student=student, job=job).exists():
        messages.info(request, 'Already applied!')
        return redirect('student_dashboard')

    score = calculate_match_score(student, job)
    application = Application.objects.create(student=student, job=job, match_score=score)

    # create connection record automatically
    Connection.objects.get_or_create(application=application)

    # notify HR
    Notification.objects.create(
        user=job.posted_by,
        message=f"New application from {request.user.username} for {job.title}."
    )

    messages.success(request, f'Applied successfully! Match score: {score}%')
    return redirect('student_dashboard')


@login_required
def contact_candidate(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    if application.job.posted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('hr_dashboard')

    if request.method == 'GET':
        return render(request, 'contact_candidate.html', {'application': application})

    if not application.can_transition_to(Application.STATUS_CONTACTED):
        messages.error(request, 'Invalid transition for application status.')
        return redirect('hr_dashboard')

    application.status = Application.STATUS_CONTACTED
    application.contacted_at = timezone.now()
    application.save()

    connection, created = Connection.objects.get_or_create(application=application)
    connection.hr_contacted = True
    connection.contacted_at = timezone.now()
    connection.contact_note = request.POST.get('contact_note', connection.contact_note)
    connection.save()

    # message to candidate
    Message.objects.create(
        sender=request.user,
        receiver=application.student.user,
        job=application.job,
        content=f"HR contacted you for {application.job.title}.\nMessage: {request.POST.get('message', 'Please check your dashboard')}"
    )
    Notification.objects.create(
        user=application.student.user,
        message=f"HR contacted you for {application.job.title}."
    )

    messages.success(request, 'Candidate contacted successfully.')
    return redirect('hr_dashboard')


@login_required
def shortlist_candidate(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    if application.job.posted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('hr_dashboard')

    if request.method == 'GET':
        return render(request, 'shortlist_candidate.html', {'application': application})

    if not application.can_transition_to(Application.STATUS_SHORTLISTED):
        messages.error(request, 'Invalid status transition.')
        return redirect('hr_dashboard')

    application.status = Application.STATUS_SHORTLISTED
    application.save()
    Notification.objects.create(user=application.student.user, message=f"You are shortlisted for {application.job.title}.")
    messages.success(request, 'Candidate shortlisted.')
    return redirect('hr_dashboard')


@login_required
def set_application_result(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    if application.job.posted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('hr_dashboard')

    if request.method == 'GET':
        return render(request, 'set_result.html', {'application': application})

    result = request.POST.get('result')
    if result not in [application.STATUS_SELECTED, application.STATUS_REJECTED]:
        messages.error(request, 'Invalid result')
        return redirect('hr_dashboard')

    if not application.can_transition_to(result):
        messages.error(request, 'Invalid status transition.')
        return redirect('hr_dashboard')

    application.status = result
    application.save()
    Notification.objects.create(user=application.student.user, message=f"Your application status changed to {result}.")
    messages.success(request, 'Application result updated.')
    return redirect('hr_dashboard')


@login_required
def mark_notifications_read(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    notifications.update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def schedule_interview(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    if application.job.posted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('hr_dashboard')

    if request.method == 'GET':
        return render(request, 'schedule_interview.html', {'application': application})

    if not application.can_transition_to(Application.STATUS_INTERVIEW):
        messages.error(request, 'Invalid transition for interview scheduling.')
        return redirect('hr_dashboard')

    datetime_str = request.POST.get('scheduled_at')
    mode = request.POST.get('mode', Interview.MODE_ONLINE)
    notes = request.POST.get('notes', '')

    try:
        scheduled_at = timezone.datetime.fromisoformat(datetime_str)
    except Exception:
        messages.error(request, 'Invalid datetime format.')
        return redirect('hr_dashboard')

    interview, _ = Interview.objects.update_or_create(
        application=application,
        defaults={
            'scheduled_at': scheduled_at,
            'mode': mode,
            'notes': notes,
            'status': Interview.STATUS_PENDING,
        }
    )

    application.status = Application.STATUS_INTERVIEW
    application.save()

    Notification.objects.create(
        user=application.student.user,
        message=f"Interview scheduled for {application.job.title} on {scheduled_at}."
    )

    messages.success(request, 'Interview scheduled successfully.')
    return redirect('hr_dashboard')


@login_required
def hr_view_student(request, student_id):
    profile = Profile.objects.filter(user=request.user, role='hr').first()
    if not profile:
        messages.error(request, 'Unauthorized')
        return redirect('home')

    student = get_object_or_404(Student, id=student_id)
    applications = Application.objects.filter(student=student).select_related('job').order_by('-applied_at')
    return render(request, 'hr_view_student.html', {
        'student': student,
        'applications': applications,
    })


@login_required
def update_interview_status(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    if request.user != interview.application.student.user and request.user != interview.application.job.posted_by:
        messages.error(request, 'Permission denied.')
        return redirect('home')

    if request.method == 'GET':
        return render(request, 'update_interview_status.html', {'interview': interview})

    new_status = request.POST.get('status')
    if new_status not in dict(Interview.STATUS_CHOICES):
        messages.error(request, 'Invalid status.')
        return redirect('home')

    interview.status = new_status
    interview.save()

    if request.user == interview.application.student.user and new_status == Interview.STATUS_RESCHEDULE_REQUESTED:
        Notification.objects.create(
            user=interview.application.job.posted_by,
            message=f"Student requested reschedule for interview on {interview.scheduled_at}."
        )

    Notification.objects.create(
        user=interview.application.student.user,
        message=f"Interview status updated to {new_status}."
    )

    messages.success(request, 'Interview status updated.')
    return redirect('home')

@login_required
def reply_message(request, message_id):
    original_msg = get_object_or_404(Message, id=message_id)
    if request.user != original_msg.receiver:
        messages.error(request, 'Permission denied.')
        return redirect('home')
        
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                receiver=original_msg.sender,
                job=original_msg.job,
                content=content
            )
            Notification.objects.create(
                user=original_msg.sender,
                message=f"New message from {request.user.username}."
            )
            messages.success(request, 'Reply sent successfully.')
            
            try:
                profile = Profile.objects.get(user=request.user)
                return redirect('student_dashboard' if profile.role == 'student' else 'hr_dashboard')
            except Profile.DoesNotExist:
                return redirect('home')
                
    return render(request, 'reply_message.html', {'original_msg': original_msg})
