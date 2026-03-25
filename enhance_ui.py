import os
import re

BASE_DIR = r"C:\Users\Sejal\OneDrive\Desktop\Ai Driven\HR_connect"
APP_DIR = os.path.join(BASE_DIR, "app")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

# 1. Update views.py with reply_message
views_path = os.path.join(APP_DIR, "views.py")
with open(views_path, "r", encoding="utf-8") as f:
    views_content = f.read()

if "def reply_message" not in views_content:
    with open(views_path, "a", encoding="utf-8") as f:
        f.write('''
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
''')

# 2. Update urls.py
urls_path = os.path.join(APP_DIR, "urls.py")
with open(urls_path, "r", encoding="utf-8") as f:
    urls_content = f.read()

if "'reply_message'" not in urls_content:
    urls_content = urls_content.replace(
        "path('notifications/mark_read/', views.mark_notifications_read, name='mark_notifications_read'),",
        "path('notifications/mark_read/', views.mark_notifications_read, name='mark_notifications_read'),\n    path('message/reply/<int:message_id>/', views.reply_message, name='reply_message'),"
    )
    with open(urls_path, "w", encoding="utf-8") as f:
        f.write(urls_content)

# 3. Write reply_message.html
reply_html = """{% extends 'base.html' %}
{% block content %}
<div class="card shadow-sm mt-5">
    <div class="card-header bg-primary text-white">
        <h4 class="mb-0">Reply to Message</h4>
    </div>
    <div class="card-body">
        <div class="alert alert-secondary">
            <strong>Original from {{ original_msg.sender.username }}:</strong><br/>
            {{ original_msg.content }}
        </div>
        <form method="post">
            {% csrf_token %}
            <div class="mb-3">
                <label class="form-label">Your Reply</label>
                <textarea name="content" class="form-control" rows="4" required placeholder="Type your message here..."></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Send Reply</button>
            <a href="{% url 'home' %}" class="btn btn-secondary">Cancel</a>
        </form>
    </div>
</div>
{% endblock %}
"""
with open(os.path.join(TEMPLATES_DIR, "reply_message.html"), "w", encoding="utf-8") as f:
    f.write(reply_html)


# 4. Overwrite hr_dashboard.html
hr_dashboard_html = """{% extends 'base.html' %}
{% block title %}HR Dashboard - AI Output{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h2>HR Manager Dashboard</h2>
    <a href="{% url 'post_job' %}" class="btn btn-success">➕ Post New Job</a>
</div>

<div class="row">
    <!-- Messages and Notifications Panel -->
    <div class="col-md-4 order-md-2 mb-4">
        <div class="card shadow-sm mb-4 border-info">
            <div class="card-header bg-info text-white">
                <h5 class="mb-0">Interactions</h5>
            </div>
            <div class="card-body p-0">
                <ul class="list-group list-group-flush">
                    <li class="list-group-item bg-light text-muted fw-bold">Recent Messages</li>
                    {% for msg in messages %}
                    <li class="list-group-item">
                        <strong>{{ msg.sender.username }}:</strong> {{ msg.content }}
                        <br/><small class="text-muted">{{ msg.created_at|timesince }} ago</small>
                        <a href="{% url 'reply_message' msg.id %}" class="btn btn-sm btn-outline-primary ms-2">Reply</a>
                    </li>
                    {% empty %}
                    <li class="list-group-item">No messages yet.</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>

    <!-- Candidate Pipeline Panel -->
    <div class="col-md-8 order-md-1">
        {% for job_app in job_applications %}
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">{{ job_app.job.title }}</h5>
            </div>
            <div class="card-body bg-light">
                <h6 class="text-secondary fw-bold border-bottom pb-2">Top AI Ranked Candidates</h6>
                <div class="row">
                    {% for app in job_app.applications %}
                    <div class="col-12 mb-3">
                        <div class="card border-0 shadow-sm">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <h5 class="card-title text-primary mb-0">{{ app.student.user.get_full_name|default:app.student.user.username }}</h5>
                                    <span class="badge bg-{% if app.match_score > 70 %}success{% elif app.match_score >= 40 %}warning text-dark{% else %}danger{% endif %} fs-6">
                                        AI Match: {{ app.match_score }}%
                                    </span>
                                </div>
                                <hr/>
                                <div class="row">
                                    <div class="col-md-8">
                                        <p class="mb-1"><strong>Degree:</strong> {{ app.student.degree }} {{ app.student.branch }} ({{ app.student.college }}, {{ app.student.passing_year }})</p>
                                        <p class="mb-1"><strong>Skills:</strong> {{ app.student.skills }}</p>
                                    </div>
                                    <div class="col-md-4 text-md-end">
                                        <span class="badge bg-secondary mb-2 px-3 py-2 fs-6 border border-dark">Status: {{ app.status }}</span><br/>
                                        {% if app.student.resume %}
                                            <a href="{{ app.student.resume.url }}" target="_blank" class="btn btn-sm btn-outline-dark">View Resume</a>
                                        {% endif %}
                                    </div>
                                </div>
                                <div class="mt-3 bg-light p-2 rounded">
                                    <strong>Actions:</strong>
                                    {% if app.status == 'Applied' %}
                                        <a href="{% url 'shortlist_candidate' app.id %}" class="btn btn-sm btn-success">Shortlist</a>
                                        <a href="{% url 'contact_candidate' app.id %}" class="btn btn-sm btn-info text-white">Contact</a>
                                    {% elif app.status == 'Shortlisted' %}
                                        <a href="{% url 'contact_candidate' app.id %}" class="btn btn-sm btn-info text-white">Contact</a>
                                        <a href="{% url 'schedule_interview' app.id %}" class="btn btn-sm btn-warning text-dark">Schedule Interview</a>
                                    {% elif app.status == 'Contacted' %}
                                        <a href="{% url 'schedule_interview' app.id %}" class="btn btn-sm btn-warning text-dark">Schedule Interview</a>
                                        <a href="{% url 'set_application_result' app.id %}" class="btn btn-sm btn-primary">Set Result</a>
                                    {% elif app.status == 'Interview Scheduled' %}
                                        <a href="{% url 'set_application_result' app.id %}" class="btn btn-sm btn-primary">Set Result</a>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% empty %}
                    <div class="col-12"><p class="text-muted">No applicants for this job yet.</p></div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% empty %}
        <div class="alert alert-info border-0 shadow-sm">
            You haven't posted any jobs yet. Connect with students by posting an opportunity!
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""
with open(os.path.join(TEMPLATES_DIR, "hr_dashboard.html"), "w", encoding="utf-8") as f:
    f.write(hr_dashboard_html)

# 5. Overwrite student_dashboard.html
student_dashboard_html = """{% extends 'base.html' %}
{% block title %}Student AI Dashboard{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4 pb-2 border-bottom">
    <h2>🎓 Student Portal</h2>
    <a href="{% url 'update_student_profile' %}" class="btn btn-outline-primary">Edit Profile</a>
</div>

<div class="row">
    <!-- Left Column -->
    <div class="col-md-4">
        <div class="card shadow-sm mb-4 border-0">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">My Profile Info</h5>
            </div>
            <div class="card-body">
                <div class="mb-3 text-center">
                    <div class="display-1 text-primary">👨‍🎓</div>
                    <h5 class="mt-2">{{ student.user.first_name }} {{ student.user.last_name }}</h5>
                    <p class="text-muted mb-0">{{ student.degree }} in {{ student.branch }}</p>
                </div>
                <div class="progress mb-2" style="height: 25px;">
                    <div class="progress-bar progress-bar-width bg-success" role="progressbar" data-strength="{{ profile_strength }}">{{ profile_strength }}% Profile Strength</div>
                </div>
                <hr>
                <p><strong>🎓 College:</strong> {{ student.college }} ({{ student.passing_year }})</p>
                <p><strong>💻 Skills:</strong> {{ student.skills }}</p>
                <p><strong>📩 Contact:</strong> {{ student.phone_number }}</p>
            </div>
        </div>

        <div class="card shadow-sm mb-4 border-primary">
            <div class="card-header bg-white border-bottom-0">
                <h5 class="text-primary mb-0"><i class="bi bi-robot"></i> Interactions & Inbox</h5>
            </div>
            <div class="card-body p-0">
                <ul class="list-group list-group-flush text-sm">
                {% if messages %}
                    {% for msg in messages %}
                    <li class="list-group-item fw-light">
                        <strong>{{ msg.sender.username }}:</strong> {{ msg.content }}
                        <br/>
                        <a href="{% url 'reply_message' msg.id %}" class="btn btn-sm py-0 mt-1 btn-primary">Reply</a>
                    </li>
                    {% endfor %}
                {% else %}
                    <li class="list-group-item text-muted">No messages in inbox.</li>
                {% endif %}
                </ul>
            </div>
        </div>
    </div>

    <!-- Right Column -->
    <div class="col-md-8">
        
        <div class="alert alert-info shadow-sm d-flex justify-content-between align-items-center">
            <div>
                <strong>🧠 AI Matching Logic:</strong> The platform scores you for jobs using real AI logic:<br/>
                <span class="badge bg-primary">50% Skills</span> + <span class="badge bg-secondary">30% Resume Keyword Parsing</span> + <span class="badge bg-dark">20% Education Match</span>
            </div>
        </div>

        <!-- Job Applications Workflow -->
        <div class="card shadow-sm mb-4 border-0">
            <div class="card-header bg-dark text-white">
                <h5 class="mb-0">🚀 My Active Applications Tracker</h5>
            </div>
            <div class="card-body bg-light">
                {% if applications %}
                    <div class="row">
                    {% for app in applications %}
                        <div class="col-md-6 mb-3">
                            <div class="card h-100 border-1 border-secondary">
                                <div class="card-body">
                                    <h5 class="card-title text-primary">{{ app.job.title }}</h5>
                                    <h6 class="card-subtitle mb-2 text-muted">{{ app.job.company }}</h6>
                                    <hr class="my-1"/>
                                    <p class="mb-1 fw-bold border border-info rounded px-2 py-1 bg-white text-center">Status: {{ app.status }}</p>
                                    <p class="mb-0 text-center"><small>AI Fit Score: {{ app.match_score }}%</small></p>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                    </div>
                {% else %}
                    <p class="text-muted text-center py-3">No applications tracked yet.</p>
                {% endif %}
            </div>
        </div>

        <!-- Smart Job Recommendations -->
        <h3 class="mb-3 text-primary border-bottom pb-2">Top AI Recommended Jobs</h3>
        <div class="row">
            {% for match in matched_jobs %}
            <div class="col-md-6 mb-3">
                <div class="card shadow-sm h-100 border-{% if match.label == 'Highly Relevant' %}success{% elif match.label == 'Moderate Match' %}warning{% else %}danger{% endif %} border-2">
                    <div class="card-body">
                        <h5 class="card-title fw-bold">{{ match.job.title }}</h5>
                        <h6 class="card-subtitle mb-3 text-muted">at {{ match.job.company }}</h6>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="fs-5 fw-bold text-{% if match.label == 'Highly Relevant' %}success{% elif match.label == 'Moderate Match' %}warning{% else %}danger{% endif %}">
                                {{ match.score }}% Fit
                            </span>
                            <span class="badge bg-dark px-2 py-1">{{ match.label }}</span>
                        </div>
                        <p class="card-text small text-muted text-truncate">Req: {{ match.job.skills_required }}</p>
                        <hr class="my-2"/>
                        <a href="{% url 'apply_job' match.job.id %}" class="btn btn-outline-primary w-100 mt-2">View & Apply</a>
                    </div>
                </div>
            </div>
            {% empty %}
            <div class="col-12">
                <div class="alert alert-warning">No recommended jobs matching your profile. Update your skills!</div>
            </div>
            {% endfor %}
        </div>

        {% if interviews %}
        <div class="card shadow-sm mt-4 border-warning border-3">
            <div class="card-header bg-warning text-dark fw-bold">📅 Upcoming Interviews</div>
            <ul class="list-group list-group-flush">
                {% for interview in interviews %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong>{{ interview.application.job.title }}</strong><br/>
                        <small>Mode: {{ interview.mode }} | On: {{ interview.scheduled_at }}</small>
                    </div>
                    {% if interview.status == 'Pending' %}
                        <a href="{% url 'update_interview_status' interview.id %}" class="btn btn-sm btn-success">Confirm/Reschedule</a>
                    {% else %}
                        <span class="badge bg-secondary">{{ interview.status }}</span>
                    {% endif %}
                </li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}

    </div>
</div>
{% endblock %}
"""
with open(os.path.join(TEMPLATES_DIR, "student_dashboard.html"), "w", encoding="utf-8") as f:
    f.write(student_dashboard_html)

print("UI Enhanced and Connection Flow Completed Successfully!")
