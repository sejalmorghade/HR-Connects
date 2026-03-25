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
                        text += page.extract_text()
                    return text.lower()
            elif self.resume.name.endswith('.txt'):
                with self.resume.open('r') as f:
                    return f.read().lower()
        except:
            return ''
        return ''

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
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    match_score = models.FloatField()
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} applied to {self.job}"
