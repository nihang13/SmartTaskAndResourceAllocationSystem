from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Skill, UserProfile, Task, AllocationLog
from .algorithms import run_smart_allocation


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Resource Profile & Capacity'
    filter_horizontal = ('skills',)


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_capacity', 'get_availability', 'is_staff')

    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '-'
    get_role.short_description = 'Role'

    def get_capacity(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.current_workload} / {obj.profile.max_capacity} tasks"
        return '-'
    get_capacity.short_description = 'Workload'

    def get_availability(self, obj):
        return obj.profile.is_available if hasattr(obj, 'profile') else '-'
    get_availability.short_description = 'Available'
    get_availability.boolean = True


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'task_count', 'profile_count')
    list_filter = ('category',)
    search_fields = ('name', 'description')

    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Required in Tasks'

    def profile_count(self, obj):
        return obj.profiles.count()
    profile_count.short_description = 'Qualified Members'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'max_capacity', 'current_load', 'is_available')
    list_filter = ('role', 'is_available')
    filter_horizontal = ('skills',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def current_load(self, obj):
        return f"{obj.current_workload} / {obj.max_capacity} ({obj.workload_percentage}%)"
    current_load.short_description = 'Current Load'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'required_skill', 'assigned_to', 'status', 'deadline', 'is_overdue')
    list_filter = ('priority', 'status', 'required_skill', 'deadline')
    search_fields = ('title', 'description', 'assigned_to__username')
    date_hierarchy = 'deadline'
    actions = ['allocate_selected_tasks', 'mark_as_completed']

    @admin.action(description="Run Smart Allocation on selected tasks")
    def allocate_selected_tasks(self, request, queryset):
        pending_qs = queryset.filter(status='PENDING', assigned_to__isnull=True)
        results = run_smart_allocation(task_queryset=pending_qs)
        self.message_user(
            request,
            f"Smart Allocation run: {results['assigned_count']} assigned, {results['unassigned_count']} unassigned."
        )

    @admin.action(description="Mark selected tasks as Completed")
    def mark_as_completed(self, request, queryset):
        count = queryset.update(status='COMPLETED')
        self.message_user(request, f"{count} task(s) marked as Completed.")


@admin.register(AllocationLog)
class AllocationLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'assigned_user', 'match_score', 'allocation_type', 'allocated_at')
    list_filter = ('allocation_type', 'allocated_at')
    search_fields = ('task__title', 'assigned_user__username', 'reason')
    readonly_fields = ('task', 'assigned_user', 'match_score', 'reason', 'allocation_type', 'allocated_at')

    def has_add_permission(self, request):
        return False
