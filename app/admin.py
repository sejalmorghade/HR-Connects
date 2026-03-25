from django.contrib import admin
from .models import Profile, Student, Job, Application

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company', 'phone_number']
    list_filter = ['role']
    search_fields = ['user__username', 'company']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['user', 'college', 'degree', 'branch', 'passing_year', 'cgpa']
    list_filter = ['college', 'branch', 'passing_year']
    search_fields = ['user__username', 'college', 'branch', 'skills']
    readonly_fields = ['user']

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'posted_by', 'created_at']
    list_filter = ['created_at', 'company']
    search_fields = ['title', 'company', 'skills_required']
    readonly_fields = ['posted_by', 'created_at']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['student', 'job', 'match_score', 'applied_at']
    list_filter = ['applied_at', 'match_score']
    search_fields = ['student__user__username', 'job__title']
    readonly_fields = ['student', 'job', 'applied_at']
