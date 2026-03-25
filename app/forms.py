from django import forms
from .models import Student, Job

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['degree', 'branch', 'college', 'passing_year', 'skills', 'resume', 'phone_number', 'address', 'date_of_birth', 'gender', 'cgpa', 'linkedin_profile', 'github_profile', 'preferred_location']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'skills_required', 'education_required', 'keywords']