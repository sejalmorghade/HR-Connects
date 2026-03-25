# AI-Driven Campus Placement and HR Connect Platform

A Django-based platform that intelligently connects students and recruiters using skill matching, education matching, and resume keyword analysis.

## Features

- **Student Module**: Registration, profile management, resume upload, job matching
- **HR Module**: Job posting, applicant management
- **Smart Matching**: 50% skill match, 30% resume keywords, 20% education match
- **Clean UI**: Bootstrap 5 responsive design

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py makemigrations && python manage.py migrate`
4. Create superuser: `python manage.py createsuperuser`
5. Run server: `python manage.py runserver`

## Deployment on Render

1. Create a Render account at https://render.com
2. Connect your GitHub repository
3. Create a new Web Service
4. Set build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
5. Set start command: `gunicorn HR_connect.wsgi:application`
6. Add environment variables:
   - `DEBUG=False`
   - `SECRET_KEY=your-secret-key`
   - `ALLOWED_HOSTS=your-render-domain`
7. Deploy

## Usage

- Register as Student or HR
- Students: Update profile, view matched jobs, apply
- HR: Post jobs, view applicants with match scores

## Matching Logic

Match Score = 0.5 _ Skill Match + 0.3 _ Resume Match + 0.2 \* Education Match

- Highly Relevant: >70%
- Moderate Match: 40-70%
- Low Match: <40%
