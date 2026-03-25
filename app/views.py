from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Profile, Student, Job, Application
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
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        role = request.POST.get('role')
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
    return render(request, 'register.html', {'form': form})

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

    return render(request, 'student_dashboard.html', {
        'student': student,
        'matched_jobs': matched_jobs,
        'profile_strength': profile_strength
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
        applications = Application.objects.filter(job=job).select_related('student__user')
        job_applications.append({
            'job': job,
            'applications': applications
        })

    return render(request, 'hr_dashboard.html', {'job_applications': job_applications})

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
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return redirect('register')

    job = get_object_or_404(Job, id=job_id)
    if Application.objects.filter(student=student, job=job).exists():
        messages.info(request, 'Already applied!')
        return redirect('student_dashboard')

    score = calculate_match_score(student, job)
    Application.objects.create(student=student, job=job, match_score=score)
    messages.success(request, f'Applied successfully! Match score: {score}%')
    return redirect('student_dashboard')
