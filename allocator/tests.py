from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Skill, UserProfile, Task, AllocationLog
from .algorithms import SmartAllocationEngine, run_smart_allocation


class SmartAllocationAlgorithmTests(TestCase):
    def setUp(self):
        self.skill_python = Skill.objects.create(
            name="Python Backend", category="SOFTWARE", description="Python development"
        )
        self.skill_design = Skill.objects.create(
            name="UI/UX Design", category="DESIGN", description="Design and prototyping"
        )
        self.skill_ml = Skill.objects.create(
            name="Machine Learning", category="DATA", description="Data science"
        )

        self.user1 = User.objects.create_user(username="alice", first_name="Alice", password="password")
        self.user1.profile.role = 'BACKEND'
        self.user1.profile.max_capacity = 2
        self.user1.profile.skills.add(self.skill_python)
        self.user1.profile.save()

        self.user2 = User.objects.create_user(username="bob", first_name="Bob", password="password")
        self.user2.profile.role = 'BACKEND'
        self.user2.profile.max_capacity = 3
        self.user2.profile.skills.add(self.skill_python)
        self.user2.profile.save()

        self.today = timezone.now().date()

    def test_skill_compatibility_matching(self):
        task = Task.objects.create(
            title="Build Django REST API",
            priority="HIGH",
            required_skill=self.skill_python,
            deadline=self.today + timedelta(days=3),
            status="PENDING"
        )

        results = run_smart_allocation()
        self.assertEqual(results['assigned_count'], 1)

        task.refresh_from_db()
        self.assertIsNotNone(task.assigned_to)
        self.assertIn(task.assigned_to, [self.user1, self.user2])
        self.assertEqual(task.status, 'IN_PROGRESS')

    def test_unmatched_skill_remains_unassigned(self):
        task = Task.objects.create(
            title="Train Neural Network",
            priority="MEDIUM",
            required_skill=self.skill_ml,  
            deadline=self.today + timedelta(days=5),
            status="PENDING"
        )

        results = run_smart_allocation()
        self.assertEqual(results['assigned_count'], 0)
        self.assertEqual(results['unassigned_count'], 1)

        task.refresh_from_db()
        self.assertIsNone(task.assigned_to)
        self.assertEqual(task.status, 'PENDING')

    def test_capacity_constraint_enforcement(self):
        for i in range(2):
            Task.objects.create(
                title=f"Alice Active Task {i}",
                priority="LOW",
                required_skill=self.skill_python,
                deadline=self.today + timedelta(days=10),
                status="IN_PROGRESS",
                assigned_to=self.user1
            )

        self.assertEqual(self.user1.profile.current_workload, 2)
        self.assertFalse(self.user1.profile.can_take_task)

        new_task = Task.objects.create(
            title="New Python Task",
            priority="URGENT",
            required_skill=self.skill_python,
            deadline=self.today + timedelta(days=2),
            status="PENDING"
        )

        results = run_smart_allocation()
        self.assertEqual(results['assigned_count'], 1)

        new_task.refresh_from_db()
        self.assertEqual(new_task.assigned_to, self.user2)

    def test_availability_toggle_enforcement(self):
        self.user1.profile.is_available = False
        self.user1.profile.save()

        self.user2.profile.is_available = False
        self.user2.profile.save()

        Task.objects.create(
            title="Bypassed Task",
            priority="HIGH",
            required_skill=self.skill_python,
            deadline=self.today + timedelta(days=3),
            status="PENDING"
        )

        results = run_smart_allocation()
        self.assertEqual(results['assigned_count'], 0)
        self.assertEqual(results['unassigned_count'], 1)

    def test_allocation_log_audit_creation(self):
        task = Task.objects.create(
            title="Test Audited Task",
            priority="HIGH",
            required_skill=self.skill_python,
            deadline=self.today + timedelta(days=3),
            status="PENDING"
        )

        run_smart_allocation()

        log = AllocationLog.objects.filter(task=task).first()
        self.assertIsNotNone(log)
        self.assertGreater(log.match_score, 0.0)
        self.assertIn("Compatibility:", log.reason)
        self.assertEqual(log.allocation_type, 'AUTOMATIC')

    def test_mark_task_completed_frees_capacity(self):
        task = Task.objects.create(
            title="Active Work Item",
            priority="HIGH",
            required_skill=self.skill_python,
            deadline=self.today + timedelta(days=3),
            status="IN_PROGRESS",
            assigned_to=self.user1
        )
        self.assertEqual(self.user1.profile.current_workload, 1)

        self.client.force_login(self.user1)
        response = self.client.post(f'/tasks/{task.id}/complete/')
        self.assertEqual(response.status_code, 302)

        task.refresh_from_db()
        self.assertEqual(task.status, 'COMPLETED')
        self.assertEqual(self.user1.profile.current_workload, 0)
        self.assertTrue(self.user1.profile.can_take_task)

    def test_csv_export_endpoints(self):
        res_logs = self.client.get('/logs/export/csv/')
        self.assertEqual(res_logs.status_code, 200)
        self.assertEqual(res_logs['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="smart_allocation_audit_', res_logs['Content-Disposition'])

        res_tasks = self.client.get('/tasks/export/csv/')
        self.assertEqual(res_tasks.status_code, 200)
        self.assertEqual(res_tasks['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="task_repository_', res_tasks['Content-Disposition'])


class TaskDeletePermissionTests(TestCase):

    def setUp(self):
        self.skill = Skill.objects.create(
            name="Django Architecture", category="SOFTWARE", description="Core backend"
        )
        self.today = timezone.now().date()
        self.task = Task.objects.create(
            title="Critical Mission Task",
            priority="HIGH",
            required_skill=self.skill,
            deadline=self.today + timedelta(days=5),
            status="PENDING"
        )

        self.developer = User.objects.create_user(username="dev_dan", password="password")
        self.developer.profile.role = 'BACKEND'
        self.developer.profile.save()

        self.lead = User.objects.create_user(username="lead_laura", password="password")
        self.lead.profile.role = 'LEAD'
        self.lead.profile.save()

        self.admin = User.objects.create_superuser(username="admin_alex", password="password", email="alex@example.com")

    def test_unauthenticated_user_cannot_delete_task(self):
        response = self.client.get(f'/tasks/{self.task.id}/delete/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

        post_response = self.client.post(f'/tasks/{self.task.id}/delete/')
        self.assertEqual(post_response.status_code, 302)
        self.assertIn('/login/', post_response.url)

        self.assertTrue(Task.objects.filter(id=self.task.id).exists())

    def test_regular_role_user_cannot_delete_task(self):
        self.client.force_login(self.developer)

        response = self.client.get(f'/tasks/{self.task.id}/delete/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/task_list.html')
        messages = list(response.context['messages'])
        self.assertTrue(any("Permission denied" in str(m) for m in messages))

        post_response = self.client.post(f'/tasks/{self.task.id}/delete/', follow=True)
        self.assertEqual(post_response.status_code, 200)
        messages = list(post_response.context['messages'])
        self.assertTrue(any("Permission denied" in str(m) for m in messages))

        self.assertTrue(Task.objects.filter(id=self.task.id).exists())

    def test_team_lead_can_delete_task(self):
        self.client.force_login(self.lead)

        response = self.client.get(f'/tasks/{self.task.id}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'allocator/task_confirm_delete.html')

        post_response = self.client.post(f'/tasks/{self.task.id}/delete/', follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_admin_can_delete_task(self):
        self.client.force_login(self.admin)

        post_response = self.client.post(f'/tasks/{self.task.id}/delete/', follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())

    def test_delete_button_visibility_in_task_list(self):
        res_anon = self.client.get('/tasks/')
        self.assertFalse(res_anon.context['can_delete_tasks'])
        self.assertNotContains(res_anon, f'/tasks/{self.task.id}/delete/')

        self.client.force_login(self.developer)
        res_dev = self.client.get('/tasks/')
        self.assertFalse(res_dev.context['can_delete_tasks'])
        self.assertNotContains(res_dev, f'/tasks/{self.task.id}/delete/')

        self.client.force_login(self.lead)
        res_lead = self.client.get('/tasks/')
        self.assertTrue(res_lead.context['can_delete_tasks'])
        self.assertContains(res_lead, f'/tasks/{self.task.id}/delete/')

        self.client.force_login(self.admin)
        res_admin = self.client.get('/tasks/')
        self.assertTrue(res_admin.context['can_delete_tasks'])
        self.assertContains(res_admin, f'/tasks/{self.task.id}/delete/')


class ViewSecurityAndAccessControlTests(TestCase):
    def setUp(self):
        self.skill = Skill.objects.create(
            name="Testing Competency", category="QA", description="QA tests"
        )
        self.user_a = User.objects.create_user(username="member_a", password="password")
        self.user_a.profile.role = 'FRONTEND'
        self.user_a.profile.save()

        self.user_b = User.objects.create_user(username="member_b", password="password")
        self.user_b.profile.role = 'BACKEND'
        self.user_b.profile.save()

        self.lead = User.objects.create_user(username="lead_user", password="password")
        self.lead.profile.role = 'LEAD'
        self.lead.profile.save()

        self.task = Task.objects.create(
            title="Secured Task Item",
            priority="LOW",
            required_skill=self.skill,
            deadline=timezone.now().date() + timedelta(days=7),
            status="PENDING"
        )

    def test_task_create_requires_login(self):
        res_anon = self.client.get('/tasks/new/')
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn('/login/', res_anon.url)

        self.client.force_login(self.user_a)
        res_auth = self.client.get('/tasks/new/')
        self.assertEqual(res_auth.status_code, 200)

    def test_task_edit_requires_login(self):
        res_anon = self.client.get(f'/tasks/{self.task.id}/edit/')
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn('/login/', res_anon.url)

        self.client.force_login(self.user_a)
        res_auth = self.client.get(f'/tasks/{self.task.id}/edit/')
        self.assertEqual(res_auth.status_code, 200)

    def test_trigger_allocation_requires_login(self):
        res_anon = self.client.post('/allocate/')
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn('/login/', res_anon.url)

        self.client.force_login(self.lead)
        res_auth = self.client.post('/allocate/', follow=True)
        self.assertEqual(res_auth.status_code, 200)

    def test_profile_edit_permissions(self):
        res_anon = self.client.get(f'/team/{self.user_a.profile.id}/edit/')
        self.assertEqual(res_anon.status_code, 302)

        self.client.force_login(self.user_b)
        res_unauth = self.client.get(f'/team/{self.user_a.profile.id}/edit/', follow=True)
        self.assertEqual(res_unauth.status_code, 200)
        messages = list(res_unauth.context['messages'])
        self.assertTrue(any("Permission denied" in str(m) for m in messages))

        self.client.force_login(self.user_a)
        res_owner = self.client.get(f'/team/{self.user_a.profile.id}/edit/')
        self.assertEqual(res_owner.status_code, 200)

        self.client.force_login(self.lead)
        res_lead = self.client.get(f'/team/{self.user_a.profile.id}/edit/')
        self.assertEqual(res_lead.status_code, 200)

    def test_toggle_availability_permissions(self):
        res_anon = self.client.post(f'/team/{self.user_a.profile.id}/toggle-availability/')
        self.assertEqual(res_anon.status_code, 302)

        self.client.force_login(self.user_b)
        res_unauth = self.client.post(f'/team/{self.user_a.profile.id}/toggle-availability/', follow=True)
        self.assertEqual(res_unauth.status_code, 200)
        messages = list(res_unauth.context['messages'])
        self.assertTrue(any("Permission denied" in str(m) for m in messages))

        self.client.force_login(self.user_a)
        prev_status = self.user_a.profile.is_available
        res_owner = self.client.post(f'/team/{self.user_a.profile.id}/toggle-availability/', follow=True)
        self.assertEqual(res_owner.status_code, 200)
        self.user_a.profile.refresh_from_db()
        self.assertEqual(self.user_a.profile.is_available, not prev_status)

