from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('SOFTWARE', 'Software Engineering'),
        ('DESIGN', 'UI/UX Design'),
        ('DEVOPS', 'DevOps & Infrastructure'),
        ('QA', 'Quality Assurance & Testing'),
        ('DATA', 'Data & AI'),
        ('MANAGEMENT', 'Project Management'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='SOFTWARE')
    description = models.TextField(blank=True, help_text="Detailed description of the skill competency")

    class Meta:
        ordering = ['name']
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('FULL_STACK', 'Full Stack Developer'),
        ('FRONTEND', 'Frontend Developer'),
        ('BACKEND', 'Backend Developer'),
        ('DEVOPS', 'DevOps Engineer'),
        ('QA_ENGINEER', 'QA Automation Engineer'),
        ('UI_UX', 'UI/UX Designer'),
        ('DATA_ENGINEER', 'Data Engineer'),
        ('LEAD', 'Technical Team Lead'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='FULL_STACK')
    skills = models.ManyToManyField(Skill, related_name='profiles', blank=True)
    max_capacity = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of concurrent active tasks this user can handle"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Designates whether this resource is currently available to take on new tasks"
    )

    class Meta:
        ordering = ['user__username']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        full_name = self.user.get_full_name()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} - {self.get_role_display()}"

    @property
    def current_workload(self):
        return self.user.assigned_tasks.filter(status__in=['PENDING', 'IN_PROGRESS']).count()

    @property
    def workload_percentage(self):
        if self.max_capacity <= 0:
            return 100
        return min(100, round((self.current_workload / self.max_capacity) * 100))

    @property
    def remaining_capacity(self):
        return max(0, self.max_capacity - self.current_workload)

    @property
    def can_take_task(self):
        return self.is_available and (self.current_workload < self.max_capacity)

    @property
    def workload_status_badge(self):
        pct = self.workload_percentage
        if not self.is_available:
            return 'secondary'
        if pct >= 100:
            return 'danger'
        if pct >= 66:
            return 'warning'
        return 'success'

    @property
    def can_delete_tasks(self):
        return self.user.is_staff or self.user.is_superuser or self.role in ['LEAD', 'ADMIN', 'MANAGER']


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
        else:
            UserProfile.objects.create(user=instance)


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('URGENT', 'Urgent / Critical'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Allocation'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    required_skill = models.ForeignKey(
        Skill,
        on_delete=models.PROTECT,
        related_name='tasks',
        help_text="Primary technical competency required to execute this task"
    )
    deadline = models.DateField(help_text="Target completion date")
    estimated_hours = models.PositiveIntegerField(
        default=4,
        help_text="Estimated effort required in person-hours"
    )
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_tasks',
        help_text="Assigned resource (leave blank for automated allocation)"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['deadline', '-priority', 'created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return f"[{self.priority}] {self.title} ({self.get_status_display()})"

    @property
    def priority_weight(self):
        weights = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'URGENT': 4}
        return weights.get(self.priority, 1)

    @property
    def days_remaining(self):
        return (self.deadline - timezone.now().date()).days

    @property
    def is_overdue(self):
        return self.days_remaining < 0 and self.status not in ['COMPLETED', 'CANCELLED']

    @property
    def priority_badge_class(self):
        mapping = {
            'LOW': 'info',
            'MEDIUM': 'primary',
            'HIGH': 'warning',
            'URGENT': 'danger',
        }
        return mapping.get(self.priority, 'secondary')

    @property
    def status_badge_class(self):
        mapping = {
            'PENDING': 'secondary',
            'IN_PROGRESS': 'primary',
            'COMPLETED': 'success',
            'CANCELLED': 'dark',
        }
        return mapping.get(self.status, 'secondary')


class AllocationLog(models.Model):
    ALLOCATION_TYPE_CHOICES = [
        ('AUTOMATIC', 'Smart Algorithm Allocation'),
        ('MANUAL', 'Manual Override / Direct Assignment'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='allocation_logs')
    assigned_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='allocation_history')
    allocated_at = models.DateTimeField(auto_now_add=True)
    match_score = models.FloatField(
        default=0.0,
        help_text="Calculated compatibility score (0 - 100)"
    )
    reason = models.TextField(
        help_text="Explainable breakdown of factors leading to this assignment"
    )
    allocation_type = models.CharField(
        max_length=15,
        choices=ALLOCATION_TYPE_CHOICES,
        default='AUTOMATIC'
    )

    class Meta:
        ordering = ['-allocated_at']
        verbose_name = 'Allocation Log'
        verbose_name_plural = 'Allocation Logs'

    def __str__(self):
        return f"{self.task.title} -> {self.assigned_user.username} ({self.match_score:.1f} pts) at {self.allocated_at.strftime('%Y-%m-%d %H:%M')}"
