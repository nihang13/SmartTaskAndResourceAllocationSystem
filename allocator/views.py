from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg
from django.utils import timezone
from .models import Task, UserProfile, Skill, AllocationLog
from .forms import TaskForm, UserProfileForm, SkillForm
from .algorithms import run_smart_allocation


def user_can_delete_tasks(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if hasattr(user, 'profile') and user.profile.role in ['LEAD', 'ADMIN', 'MANAGER']:
        return True
    return False


def dashboard(request):
    today = timezone.now().date()
    
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='PENDING').count()
    in_progress_tasks = Task.objects.filter(status='IN_PROGRESS').count()
    completed_tasks = Task.objects.filter(status='COMPLETED').count()
    overdue_tasks = Task.objects.filter(
        deadline__lt=today,
        status__in=['PENDING', 'IN_PROGRESS']
    ).count()

    profiles = UserProfile.objects.select_related('user').prefetch_related('skills', 'user__assigned_tasks')
    total_resources = profiles.count()
    available_resources = profiles.filter(is_available=True).count()

    utilization_list = [p.workload_percentage for p in profiles] if total_resources > 0 else [0]
    avg_utilization = round(sum(utilization_list) / max(1, len(utilization_list)), 1)

    urgent_pending = Task.objects.filter(
        status='PENDING',
        assigned_to__isnull=True
    ).select_related('required_skill').order_by('-priority', 'deadline')[:6]

    recent_logs = AllocationLog.objects.select_related('task', 'assigned_user').order_by('-allocated_at')[:8]

    priority_counts = {
        'URGENT': Task.objects.filter(priority='URGENT').count(),
        'HIGH': Task.objects.filter(priority='HIGH').count(),
        'MEDIUM': Task.objects.filter(priority='MEDIUM').count(),
        'LOW': Task.objects.filter(priority='LOW').count(),
    }

    context = {
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'total_resources': total_resources,
        'available_resources': available_resources,
        'avg_utilization': avg_utilization,
        'urgent_pending': urgent_pending,
        'recent_logs': recent_logs,
        'profiles': profiles,
        'priority_counts': priority_counts,
    }
    return render(request, 'allocator/dashboard.html', context)


def task_list(request):
    tasks = Task.objects.select_related('required_skill', 'assigned_to', 'assigned_to__profile')

    status_filter = request.GET.get('status', '').strip()
    priority_filter = request.GET.get('priority', '').strip()
    skill_filter = request.GET.get('skill', '').strip()
    search_query = request.GET.get('q', '').strip()

    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if skill_filter:
        tasks = tasks.filter(required_skill_id=skill_filter)
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    all_skills = Skill.objects.all()

    context = {
        'tasks': tasks,
        'all_skills': all_skills,
        'selected_status': status_filter,
        'selected_priority': priority_filter,
        'selected_skill': skill_filter,
        'search_query': search_query,
        'can_delete_tasks': user_can_delete_tasks(request.user),
    }
    return render(request, 'allocator/task_list.html', context)


@login_required(login_url='login')
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            if task.assigned_to:
                AllocationLog.objects.create(
                    task=task,
                    assigned_user=task.assigned_to,
                    match_score=100.0,
                    reason=f"Manual allocation assigned directly by administrator upon task creation.",
                    allocation_type='MANUAL'
                )
                if task.status == 'PENDING':
                    task.status = 'IN_PROGRESS'
                    task.save(update_fields=['status'])

            messages.success(request, f"Task '{task.title}' created successfully!")
            return redirect('task_list')
    else:
        form = TaskForm()

    return render(request, 'allocator/task_form.html', {'form': form, 'action_title': 'Create New Task'})


@login_required(login_url='login')
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    old_assigned_user = task.assigned_to

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save()
            if updated_task.assigned_to and updated_task.assigned_to != old_assigned_user:
                AllocationLog.objects.create(
                    task=updated_task,
                    assigned_user=updated_task.assigned_to,
                    match_score=100.0,
                    reason="Manual reassignment performed via task edit screen.",
                    allocation_type='MANUAL'
                )
                if updated_task.status == 'PENDING':
                    updated_task.status = 'IN_PROGRESS'
                    updated_task.save(update_fields=['status'])

            messages.success(request, f"Task '{updated_task.title}' updated successfully!")
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)

    return render(request, 'allocator/task_form.html', {
        'form': form,
        'task': task,
        'action_title': f'Edit Task: {task.title}'
    })


@login_required(login_url='login')
def task_delete(request, pk):
    if not user_can_delete_tasks(request.user):
        messages.error(request, "Permission denied: Only administrators or team leads can delete tasks.")
        return redirect('task_list')

    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        title = task.title
        task.delete()
        messages.success(request, f"Task '{title}' has been deleted.")
        return redirect('task_list')

    return render(request, 'allocator/task_confirm_delete.html', {'task': task})


@login_required(login_url='login')
def trigger_auto_allocation(request):
    if request.method == 'POST' or request.GET.get('confirm') == '1':
        results = run_smart_allocation()

        assigned_count = results['assigned_count']
        unassigned_count = results['unassigned_count']

        if results['total_tasks'] == 0:
            messages.info(request, "No pending tasks required allocation.")
        elif assigned_count > 0 and unassigned_count == 0:
            messages.success(
                request,
                f"Smart Allocation Success! All {assigned_count} pending task(s) were successfully matched and assigned to optimal resources."
            )
        elif assigned_count > 0 and unassigned_count > 0:
            messages.warning(
                request,
                f"Partial Allocation: {assigned_count} task(s) assigned successfully, but {unassigned_count} task(s) could not be matched due to capacity limits or missing skill sets."
            )
        else:
            messages.error(
                request,
                f"Allocation Failed: Unable to assign {unassigned_count} task(s). Team members may be at full capacity or lack required technical skills."
            )

        return redirect('allocation_logs')

    pending_count = Task.objects.filter(status='PENDING', assigned_to__isnull=True).count()
    return render(request, 'allocator/allocation_confirm.html', {'pending_count': pending_count})


def user_profiles(request):
    profiles = UserProfile.objects.select_related('user').prefetch_related('skills').all()
    all_skills = Skill.objects.all()

    context = {
        'profiles': profiles,
        'all_skills': all_skills,
    }
    return render(request, 'allocator/user_profiles.html', context)


@login_required(login_url='login')
def profile_edit(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    is_owner = (request.user == profile.user)
    is_lead_or_admin = user_can_delete_tasks(request.user)

    if not (is_owner or is_lead_or_admin):
        messages.error(request, "Permission denied: You can only edit your own profile or manage profiles as an administrator/team lead.")
        return redirect('user_profiles')

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Profile for {profile.user.username} updated successfully!")
            return redirect('user_profiles')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'allocator/profile_form.html', {
        'form': form,
        'profile': profile,
    })


@login_required(login_url='login')
def toggle_availability(request, pk):
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, pk=pk)
        is_owner = (request.user == profile.user)
        is_lead_or_admin = user_can_delete_tasks(request.user)

        if not (is_owner or is_lead_or_admin):
            messages.error(request, "Permission denied: You do not have permission to modify this member's availability.")
            return redirect('user_profiles')

        profile.is_available = not profile.is_available
        profile.save(update_fields=['is_available'])
        status_text = "Available" if profile.is_available else "Unavailable"
        messages.info(request, f"{profile.user.username} is now marked as {status_text}.")
    return redirect('user_profiles')



def allocation_logs(request):
    logs = AllocationLog.objects.select_related('task', 'assigned_user', 'task__required_skill').all()
    context = {
        'logs': logs,
    }
    return render(request, 'allocator/allocation_logs.html', context)


import csv
from django.http import HttpResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required


def user_login(request):

    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, 'allocator/login.html', {'form': form})


def user_logout(request):

    auth_logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('dashboard')


@login_required(login_url='login')
def my_tasks(request):

    user = request.user
    tasks = Task.objects.filter(assigned_to=user).select_related('required_skill')

    status_filter = request.GET.get('status', 'ACTIVE')
    if status_filter == 'ACTIVE':
        filtered_tasks = tasks.filter(status__in=['PENDING', 'IN_PROGRESS'])
    elif status_filter == 'COMPLETED':
        filtered_tasks = tasks.filter(status='COMPLETED')
    else:
        filtered_tasks = tasks

    active_count = tasks.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
    completed_count = tasks.filter(status='COMPLETED').count()

    context = {
        'tasks': filtered_tasks,
        'active_count': active_count,
        'completed_count': completed_count,
        'selected_tab': status_filter,
        'profile': getattr(user, 'profile', None),
    }
    return render(request, 'allocator/my_tasks.html', context)


@login_required(login_url='login')
def mark_task_completed(request, pk):

    task = get_object_or_404(Task, pk=pk)

    if task.assigned_to != request.user and not request.user.is_staff:
        messages.error(request, "You do not have permission to modify this task.")
        return redirect('dashboard')

    if request.method == 'POST':
        task.status = 'COMPLETED'
        task.save(update_fields=['status', 'updated_at'])
        messages.success(request, f"Task '{task.title}' marked as Completed! Your capacity has been freed.")

    referer = request.META.get('HTTP_REFERER')
    if referer and 'my-tasks' in referer:
        return redirect('my_tasks')
    return redirect('task_list')


def export_allocation_logs_csv(request):

    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="smart_allocation_audit_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Log ID',
        'Timestamp (UTC)',
        'Task Title',
        'Task Priority',
        'Required Skill',
        'Assigned Resource',
        'Member Role',
        'Compatibility Score (/100)',
        'Allocation Type',
        'Algorithmic Rationale'
    ])

    logs = AllocationLog.objects.select_related('task', 'assigned_user', 'task__required_skill', 'assigned_user__profile').all()
    for log in logs:
        writer.writerow([
            log.id,
            log.allocated_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.task.title,
            log.task.priority,
            log.task.required_skill.name,
            log.assigned_user.get_full_name() or log.assigned_user.username,
            getattr(log.assigned_user.profile, 'get_role_display', lambda: '-')(),
            f"{log.match_score:.2f}",
            log.allocation_type,
            log.reason
        ])

    return response


def export_tasks_csv(request):

    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="task_repository_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Task ID',
        'Title',
        'Priority',
        'Status',
        'Required Skill',
        'Assigned Resource',
        'Deadline',
        'Estimated Hours',
        'Created At'
    ])

    tasks = Task.objects.select_related('required_skill', 'assigned_to').all()
    for t in tasks:
        assignee = t.assigned_to.get_full_name() or t.assigned_to.username if t.assigned_to else 'Unassigned'
        writer.writerow([
            t.id,
            t.title,
            t.priority,
            t.status,
            t.required_skill.name,
            assignee,
            t.deadline.strftime('%Y-%m-%d'),
            t.estimated_hours,
            t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return response

