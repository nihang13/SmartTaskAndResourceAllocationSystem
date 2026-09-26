from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from allocator.models import Skill, UserProfile, Task, AllocationLog


class Command(BaseCommand):
    help = 'Seeds database with realistic skills, users, profiles, and pending/assigned tasks for demo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing demo data seeding..."))

        # 1. Create Skills
        skills_data = [
            {'name': 'Python Backend', 'category': 'SOFTWARE', 'description': 'Django, FastAPI, REST APIs, asynchronous tasks'},
            {'name': 'Frontend & UI', 'category': 'DESIGN', 'description': 'React, HTML5, CSS3, modern responsive layouts'},
            {'name': 'Database Architecture', 'category': 'SOFTWARE', 'description': 'PostgreSQL, query optimization, indexing, schema design'},
            {'name': 'DevOps & CI/CD', 'category': 'DEVOPS', 'description': 'Docker, Kubernetes, GitHub Actions, Linux administration'},
            {'name': 'QA & Test Automation', 'category': 'QA', 'description': 'Pytest, Selenium, integration testing, test plans'},
            {'name': 'UI/UX Prototyping', 'category': 'DESIGN', 'description': 'Figma, user research, wireframing, design systems'},
            {'name': 'Machine Learning', 'category': 'DATA', 'description': 'Scikit-learn, PyTorch, predictive modeling, data pipelines'},
        ]

        skills_dict = {}
        for s in skills_data:
            skill, _ = Skill.objects.get_or_create(
                name=s['name'],
                defaults={'category': s['category'], 'description': s['description']}
            )
            skills_dict[s['name']] = skill

        self.stdout.write(self.style.SUCCESS(f"Created/verified {len(skills_dict)} skills."))

        # 2. Create Users & Profiles
        users_data = [
            {
                'username': 'alice_dev',
                'first_name': 'Alice',
                'last_name': 'Vance',
                'email': 'alice@example.com',
                'role': 'BACKEND',
                'max_capacity': 3,
                'skills': ['Python Backend', 'Database Architecture'],
                'is_available': True,
            },
            {
                'username': 'bob_designer',
                'first_name': 'Bob',
                'last_name': 'Sterling',
                'email': 'bob@example.com',
                'role': 'UI_UX',
                'max_capacity': 4,
                'skills': ['Frontend & UI', 'UI/UX Prototyping'],
                'is_available': True,
            },
            {
                'username': 'charlie_ops',
                'first_name': 'Charlie',
                'last_name': 'Reid',
                'email': 'charlie@example.com',
                'role': 'DEVOPS',
                'max_capacity': 3,
                'skills': ['DevOps & CI/CD', 'Python Backend'],
                'is_available': True,
            },
            {
                'username': 'diana_qa',
                'first_name': 'Diana',
                'last_name': 'Prince',
                'email': 'diana@example.com',
                'role': 'QA_ENGINEER',
                'max_capacity': 3,
                'skills': ['QA & Test Automation', 'Python Backend'],
                'is_available': True,
            },
            {
                'username': 'evan_fullstack',
                'first_name': 'Evan',
                'last_name': 'Wright',
                'email': 'evan@example.com',
                'role': 'FULL_STACK',
                'max_capacity': 4,
                'skills': ['Python Backend', 'Frontend & UI', 'Database Architecture'],
                'is_available': True,
            },
        ]

        created_users = {}
        for u in users_data:
            user, created = User.objects.get_or_create(
                username=u['username'],
                defaults={
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'email': u['email'],
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()

            profile = user.profile
            profile.role = u['role']
            profile.max_capacity = u['max_capacity']
            profile.is_available = u['is_available']
            profile.save()

            # Assign skills
            for skill_name in u['skills']:
                profile.skills.add(skills_dict[skill_name])

            created_users[u['username']] = user

        self.stdout.write(self.style.SUCCESS(f"Created/verified {len(created_users)} team members."))

        # Create superuser if not exists
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            admin_user.first_name = "System"
            admin_user.last_name = "Admin"
            admin_user.save()
            admin_user.profile.role = 'LEAD'
            admin_user.profile.save()
            admin_user.profile.skills.add(*skills_dict.values())
            self.stdout.write(self.style.SUCCESS("Created admin superuser: admin / admin123"))

        # 3. Create Sample Tasks (Some Pending, Some In Progress)
        today = timezone.now().date()

        tasks_data = [
            # Pending Tasks with various priorities (Ready for auto-allocation!)
            {
                'title': 'Design Zero-Trust API Authentication Endpoint',
                'description': 'Implement JWT token generation, refresh rotation, and rate-limiting middleware.',
                'priority': 'URGENT',
                'required_skill': skills_dict['Python Backend'],
                'deadline': today + timedelta(days=2),
                'estimated_hours': 8,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Refactor High-Volume Database Indexing',
                'description': 'Analyze slow query logs, optimize composite indexes on transactions table.',
                'priority': 'HIGH',
                'required_skill': skills_dict['Database Architecture'],
                'deadline': today + timedelta(days=4),
                'estimated_hours': 6,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Build Responsive Customer Dashboard View',
                'description': 'Create mobile-friendly analytics dashboard using Bootstrap and interactive widgets.',
                'priority': 'HIGH',
                'required_skill': skills_dict['Frontend & UI'],
                'deadline': today + timedelta(days=3),
                'estimated_hours': 10,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Configure Automated CI/CD Deployment Pipeline',
                'description': 'Set up GitHub Actions to run tests, build Docker containers, and deploy to staging.',
                'priority': 'URGENT',
                'required_skill': skills_dict['DevOps & CI/CD'],
                'deadline': today + timedelta(days=1),
                'estimated_hours': 6,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Develop End-to-End Regression Test Suite',
                'description': 'Write automated Pytest and UI verification tests covering user onboarding flows.',
                'priority': 'MEDIUM',
                'required_skill': skills_dict['QA & Test Automation'],
                'deadline': today + timedelta(days=5),
                'estimated_hours': 12,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Conduct User Persona Research & Wireframing',
                'description': 'Produce low-fidelity wireframes in Figma based on customer interview findings.',
                'priority': 'LOW',
                'required_skill': skills_dict['UI/UX Prototyping'],
                'deadline': today + timedelta(days=9),
                'estimated_hours': 8,
                'status': 'PENDING',
                'assigned_to': None,
            },
            {
                'title': 'Train Demand Forecasting ML Model',
                'description': 'Train initial regression baseline using scikit-learn on historical order volumes.',
                'priority': 'MEDIUM',
                'required_skill': skills_dict['Machine Learning'],
                'deadline': today + timedelta(days=7),
                'estimated_hours': 16,
                'status': 'PENDING',
                'assigned_to': None,
            },
            # Already active tasks (to test load balancing & capacity limits)
            {
                'title': 'Patch Critical SSL Certificate Expiry',
                'description': 'Renew and install wild-card SSL certificates across production ingress routers.',
                'priority': 'URGENT',
                'required_skill': skills_dict['DevOps & CI/CD'],
                'deadline': today + timedelta(days=1),
                'estimated_hours': 3,
                'status': 'IN_PROGRESS',
                'assigned_to': created_users['charlie_ops'],
            },
            {
                'title': 'Design Navigation Bar & Theme System',
                'description': 'Finalize color palette, accessibility contrast standards, and responsive header.',
                'priority': 'MEDIUM',
                'required_skill': skills_dict['UI/UX Prototyping'],
                'deadline': today + timedelta(days=4),
                'estimated_hours': 5,
                'status': 'IN_PROGRESS',
                'assigned_to': created_users['bob_designer'],
            },
            {
                'title': 'Implement Stripe Payment Webhook Listener',
                'description': 'Handle asynchronous checkout session events and update subscription state.',
                'priority': 'HIGH',
                'required_skill': skills_dict['Python Backend'],
                'deadline': today + timedelta(days=3),
                'estimated_hours': 8,
                'status': 'IN_PROGRESS',
                'assigned_to': created_users['alice_dev'],
            },
        ]

        task_count = 0
        for td in tasks_data:
            task, created = Task.objects.get_or_create(
                title=td['title'],
                defaults={
                    'description': td['description'],
                    'priority': td['priority'],
                    'required_skill': td['required_skill'],
                    'deadline': td['deadline'],
                    'estimated_hours': td['estimated_hours'],
                    'status': td['status'],
                    'assigned_to': td['assigned_to'],
                }
            )
            if created:
                task_count += 1
                if td['assigned_to']:
                    AllocationLog.objects.create(
                        task=task,
                        assigned_user=td['assigned_to'],
                        match_score=95.0,
                        reason="Pre-existing task assignment during baseline seed.",
                        allocation_type='MANUAL'
                    )

        self.stdout.write(self.style.SUCCESS(f"Seeded {task_count} demo tasks."))
        self.stdout.write(self.style.SUCCESS("Demo environment ready! You can now run the Smart Allocation algorithm."))
