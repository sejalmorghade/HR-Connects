import re
from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('student', 'Student'), ('hr', 'HR')])
    company = models.CharField(max_length=100, blank=True)  # for HR
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Student(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    degree = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    college = models.CharField(max_length=100)
    passing_year = models.IntegerField()
    skills = models.TextField()  # comma-separated
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    linkedin_profile = models.URLField(blank=True)
    github_profile = models.URLField(blank=True)
    preferred_location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

    def get_resume_text(self):
        if not self.resume:
            return ''
        try:
            if self.resume.name.endswith('.pdf'):
                import PyPDF2
                with self.resume.open('rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ''
                    return text.lower()
            elif self.resume.name.endswith('.txt'):
                with self.resume.open('r') as f:
                    return f.read().lower()
        except:
            return ''
        return ''

    @property
    def extracted_skills(self):
        analysis, _ = ResumeAnalysis.objects.get_or_create(student=self)
        if analysis.extracted_skills:
            return [skill.strip().lower() for skill in analysis.extracted_skills.split(',') if skill.strip()]
        return []

    @property
    def combined_skills(self):
        manual = [skill.strip().lower() for skill in self.skills.split(',') if skill.strip()]
        extracted = self.extracted_skills
        return sorted(set(manual + extracted))

    def update_resume_skills(self):
        text = self.get_resume_text()
        if not text:
            return []

        job_terms = set(re.findall(r"[A-Za-z+#+]+", text.lower()))
        common_skills = {'python', 'django', 'sql', 'javascript', 'react', 'java', 'c++', 'machine', 'data', 'nlp'}
        extracted = [word for word in job_terms if word in common_skills]

        analysis, _ = ResumeAnalysis.objects.get_or_create(student=self)
        analysis.raw_text = text
        analysis.extracted_skills = ", ".join(sorted(set(extracted)))
        analysis.save()
        return extracted

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    skills_required = models.TextField()  # comma-separated
    education_required = models.CharField(max_length=200)  # e.g., "B.Tech CSE"
    keywords = models.TextField(blank=True)  # comma-separated
    created_at = models.DateTimeField(auto_now_add=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE)  # HR user

    def __str__(self):
        return self.title

class Application(models.Model):
    STATUS_APPLIED = 'Applied'
    STATUS_SHORTLISTED = 'Shortlisted'
    STATUS_CONTACTED = 'Contacted'
    STATUS_INTERVIEW = 'Interview Scheduled'
    STATUS_SELECTED = 'Selected'
    STATUS_REJECTED = 'Rejected'

    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_SHORTLISTED, 'Shortlisted'),
        (STATUS_CONTACTED, 'Contacted'),
        (STATUS_INTERVIEW, 'Interview Scheduled'),
        (STATUS_SELECTED, 'Selected'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    match_score = models.FloatField(default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    contacted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'job')

    def can_transition_to(self, new_status):
        flow = {
            self.STATUS_APPLIED: [self.STATUS_SHORTLISTED, self.STATUS_CONTACTED],
            self.STATUS_SHORTLISTED: [self.STATUS_CONTACTED, self.STATUS_INTERVIEW],
            self.STATUS_CONTACTED: [self.STATUS_INTERVIEW, self.STATUS_SELECTED, self.STATUS_REJECTED],
            self.STATUS_INTERVIEW: [self.STATUS_SELECTED, self.STATUS_REJECTED],
            self.STATUS_SELECTED: [],
            self.STATUS_REJECTED: [],
        }
        return new_status in flow.get(self.status, [])

    def __str__(self):
        return f"{self.student} applied to {self.job} [{self.status}]"


class Connection(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    hr_contacted = models.BooleanField(default=False)
    contacted_at = models.DateTimeField(null=True, blank=True)
    contact_note = models.TextField(blank=True)

    def __str__(self):
        return f"Connection for {self.application}"


class Interview(models.Model):
    MODE_ONLINE = 'Online'
    MODE_OFFLINE = 'Offline'
    STATUS_PENDING = 'Pending'
    STATUS_CONFIRMED = 'Confirmed'
    STATUS_RESCHEDULE_REQUESTED = 'Reschedule Requested'
    STATUS_COMPLETED = 'Completed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_RESCHEDULE_REQUESTED, 'Reschedule Requested'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    mode = models.CharField(max_length=8, choices=[(MODE_ONLINE, 'Online'), (MODE_OFFLINE, 'Offline')], default=MODE_ONLINE)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Interview for {self.application} at {self.scheduled_at}"


class ResumeAnalysis(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    raw_text = models.TextField(blank=True)
    extracted_skills = models.TextField(blank=True)  # comma-separated
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ResumeAnalysis for {self.student}"


class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:40]}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def unread_count(cls, user):
        return cls.objects.filter(user=user, is_read=False).count()

    def __str__(self):
        return f"{self.user.username}: {self.message[:40]}"

