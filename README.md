# Smart Task and Resource Allocation System

A complete full-stack web application built with **Python**, **Django**, **SQLite**, and **Bootstrap 5** for a final-year university project.

Unlike typical CRUD apps, this system incorporates a **custom native Python multi-factor heuristic algorithm** (`allocator/algorithms.py`) that intelligently matches unassigned pending tasks to optimal team members based on **skill compatibility**, **team load balancing**, **capacity limits**, **priority weights**, and **deadline urgency** — without using third-party optimization blackboxes.

---

## Key Features

1. **Smart Multi-Factor Allocation Algorithm**:
   - **Hard Constraints**: Validates skill competency, availability status, and capacity thresholds.
   - **Soft Constraints (0 - 100 Score)**:
     - **Skill & Role Compatibility (40 pts)**: Primary skill matching + role synergy bonus.
     - **Workload Balancing (35 pts)**: Favors candidates with lower active workload, distributing work fairly across the team.
     - **Capacity Buffer (15 pts)**: Safeguards against overloading.
     - **Urgency & Deadline Alignment (10 pts)**: Prioritizes tight delivery windows.
   - **Dynamic Workload Tracking**: Updates simulated workloads on-the-fly during batch allocations.
   - **Explainable AI & Audit Logging**: Every assignment is recorded in `AllocationLog` with an exact mathematical rationale.

2. **Full-Featured Dashboard & Minimalist UI**:
   - Real-time KPI stat cards (Total Tasks, Pending, Active, Completed, Overdue, Team Utilization).
   - Visual workload utilization meters for each developer.
   - One-click **"Run Smart Allocation"** engine trigger with real-time flash feedback.
   - Minimalist Bootstrap 5 theme with priority badges, status pills, and interactive search/filters.

3. **Authentication & Developer Workspace ("My Tasks")**:
   - Built-in user authentication supporting developer login/logout.
   - Dedicated **"My Tasks"** workspace for logged-in team members to review their assignments.
   - One-click **"Mark Done"** feature that immediately marks the task completed and reduces active workload, demonstrating dynamic capacity restoration.

4. **Data Reporting & CSV Export**:
   - One-click download of the complete **Allocation Audit Trail** as a CSV report (`smart_allocation_audit_YYYYMMDD.csv`).
   - One-click export of the entire **Task Repository** breakdown as CSV.

5. **Task & Team Management**:
   - Complete CRUD operations for tasks (with datepicker deadlines and priority levels).
   - Team resource roster displaying verified competencies, concurrent capacity limits, and availability toggles.
   - Comprehensive audit trail table with filterable history.

6. **Zero-Setup Database**:
   - Pre-configured for **SQLite** with an automated demo data seeder command.

---

## Project Directory Layout

```
Project3/
├── manage.py                               # Django CLI entrypoint
├── requirements.txt                        # Dependency list
├── README.md                               # Setup and architecture documentation
├── db.sqlite3                              # SQLite database (created on migrate)
│
├── task_manager/                           # Project configuration package
│   ├── __init__.py
│   ├── settings.py                         # Settings (SQLite, Apps, Templates, Static)
│   ├── urls.py                             # Root routing configuration
│   ├── wsgi.py                             # WSGI entrypoint
│   └── asgi.py                             # ASGI entrypoint
│
├── allocator/                              # Core application package
│   ├── __init__.py
│   ├── admin.py                            # Customized Django Admin panel
│   ├── apps.py                             # App configuration
│   ├── models.py                           # Skill, UserProfile, Task, AllocationLog
│   ├── forms.py                            # Bootstrap 5 styled forms
│   ├── views.py                            # Dashboard, CRUD, Trigger, Logs views
│   ├── urls.py                             # App routing
│   ├── algorithms.py                       # Native Python multi-factor matching engine
│   ├── tests.py                            # Comprehensive test suite
│   │
│   ├── management/                         # Custom CLI commands
│   │   └── commands/
│   │       └── seed_demo_data.py           # Populates demo skills, users, and tasks
│   │
│   └── templates/                          # HTML5 / Bootstrap 5 Templates
│       └── allocator/
│           ├── base.html                   # Base layout with navbar & alerts
│           ├── dashboard.html              # Main KPI & allocation control center
│           ├── task_list.html              # Filterable task repository table
│           ├── task_form.html              # Task creation/editing form
│           ├── task_confirm_delete.html    # Delete confirmation modal
│           ├── user_profiles.html          # Team resources & capacity gauges
│           ├── profile_form.html           # Profile editing form
│           ├── allocation_logs.html        # Explainable AI audit trail
│           └── allocation_confirm.html     # Confirmation view for allocations
│
└── static/
    └── css/
        └── custom.css                      # Modern aesthetic enhancements
```

---

## Quickstart & Local Setup Guide

### 1. Prerequisites
Ensure you have **Python 3.10+** installed.

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Seed Realistic Demo Data
Populate the database with predefined skills, team members (developers, designers, ops), and sample pending tasks:
```bash
python manage.py seed_demo_data
```

> **Default Superuser / Admin Credentials:**
> - **Username**: `admin`
> - **Password**: `admin123`
> - **Email**: `admin@example.com`

> **Quick Demo Accounts:**
> - **Username**: `alice_dev`
> - **Password**: `demo1234`
> - **Email**: `admin@example.com`

> **Quick Demo Accounts:**
> - **Username**: `bob_designer`
> - **Password**: `demo1234`
> - **Email**: `admin@example.com`

### 6. Run the Test Suite
Verify that the matching algorithm and capacity limits pass all unit tests:
```bash
python manage.py test allocator
```

### 7. Launch the Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
- **Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Django Admin**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## How to Test the Auto-Allocation Algorithm

1. Log into the system at `http://127.0.0.1:8000/`.
2. Notice the **Pending Tasks** counter on the Dashboard.
3. Click the purple **"Run Smart Allocation"** button on the navbar or dashboard banner.
4. The custom algorithm will:
   - Calculate urgency for each pending task.
   - Match each task to eligible team members possessing the required technical skill.
   - Select the candidate with the highest multi-factor score (balancing current workload vs. max capacity).
   - Assign the task, switch its status to `IN_PROGRESS`, and log the mathematical rationale.
5. You will be redirected to the **Audit Trail** page showing the score and the exact rationale behind each allocation decision!
