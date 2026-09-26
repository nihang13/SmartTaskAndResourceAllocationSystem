from datetime import date
from django.db import transaction
from django.utils import timezone
from .models import Task, UserProfile, AllocationLog


class SmartAllocationEngine:
    WEIGHT_SKILL = 40.0       
    WEIGHT_WORKLOAD = 35.0    
    WEIGHT_BUFFER = 15.0      
    WEIGHT_URGENCY = 10.0     

    def __init__(self):
        self.today = timezone.now().date()

    def calculate_task_urgency(self, task: Task) -> float:
        priority_multiplier = {
            'URGENT': 40.0,
            'HIGH': 30.0,
            'MEDIUM': 20.0,
            'LOW': 10.0,
        }.get(task.priority, 10.0)

        days_left = (task.deadline - self.today).days
        if days_left <= 0:
            proximity_score = 30.0  
        elif days_left <= 3:
            proximity_score = 20.0
        elif days_left <= 7:
            proximity_score = 10.0
        else:
            proximity_score = max(0.0, 5.0 - (days_left * 0.2))

        return priority_multiplier + proximity_score

    def evaluate_candidate(self, task: Task, profile: UserProfile, current_workload: int) -> dict: 
        if not profile.is_available:
            return {
                'is_eligible': False,
                'ineligibility_reason': f"{profile.user.username} is marked as unavailable.",
                'total_score': 0.0,
            }

        if current_workload >= profile.max_capacity:
            return {
                'is_eligible': False,
                'ineligibility_reason': f"{profile.user.username} has reached maximum capacity ({current_workload}/{profile.max_capacity}).",
                'total_score': 0.0,
            }

        candidate_skills = profile.skills.all()
        has_skill = task.required_skill in candidate_skills
        if not has_skill:
            return {
                'is_eligible': False,
                'ineligibility_reason': f"{profile.user.username} does not possess required skill '{task.required_skill.name}'.",
                'total_score': 0.0,
            }

        skill_score = 35.0  
        role_synergies = {
            'SOFTWARE': ['FULL_STACK', 'BACKEND', 'FRONTEND', 'LEAD'],
            'DESIGN': ['UI_UX', 'FRONTEND'],
            'DEVOPS': ['DEVOPS', 'FULL_STACK', 'BACKEND'],
            'QA': ['QA_ENGINEER', 'FULL_STACK'],
            'DATA': ['DATA_ENGINEER', 'BACKEND'],
        }
        matching_roles = role_synergies.get(task.required_skill.category, [])
        if profile.role in matching_roles:
            skill_score += 5.0
        skill_score = min(self.WEIGHT_SKILL, skill_score)

        utilization_ratio = current_workload / profile.max_capacity
        workload_score = self.WEIGHT_WORKLOAD * (1.0 - utilization_ratio)

        remaining_slots = profile.max_capacity - current_workload
        buffer_ratio = min(1.0, remaining_slots / max(1, profile.max_capacity))
        buffer_score = self.WEIGHT_BUFFER * buffer_ratio


        days_left = (task.deadline - self.today).days
        urgency_factor = 0.5
        if task.priority in ['HIGH', 'URGENT']:
   
            urgency_factor = 0.9 if remaining_slots >= 2 else 0.7
        if days_left <= 2:
            urgency_factor = min(1.0, urgency_factor + 0.2)
        urgency_score = self.WEIGHT_URGENCY * urgency_factor

        total_score = round(skill_score + workload_score + buffer_score + urgency_score, 2)

        display_name = profile.user.get_full_name() or profile.user.username
        rationale = (
            f"Candidate: {display_name} | "
            f"Compatibility: {total_score:.1f}/100 pts. "
            f"[Skills: {skill_score:.1f}/40 pts (Possesses '{task.required_skill.name}')] "
            f"[Load Balancing: {workload_score:.1f}/35 pts (Active: {current_workload}/{profile.max_capacity} tasks)] "
            f"[Capacity Buffer: {buffer_score:.1f}/15 pts ({remaining_slots} open slots)] "
            f"[Priority/Urgency: {urgency_score:.1f}/10 pts]."
        )

        return {
            'is_eligible': True,
            'total_score': total_score,
            'breakdown': {
                'skill_score': skill_score,
                'workload_score': round(workload_score, 2),
                'buffer_score': round(buffer_score, 2),
                'urgency_score': round(urgency_score, 2),
            },
            'rationale': rationale,
        }

    def allocate_pending_tasks(self, task_queryset=None) -> dict:
        if task_queryset is None:
            tasks = list(Task.objects.filter(status='PENDING', assigned_to__isnull=True).select_related('required_skill'))
        else:
            tasks = list(task_queryset.filter(status='PENDING', assigned_to__isnull=True).select_related('required_skill'))

        if not tasks:
            return {
                'success': True,
                'total_tasks': 0,
                'assigned_count': 0,
                'unassigned_count': 0,
                'assignments': [],
                'unassigned': [],
                'message': 'No pending tasks awaiting allocation.'
            }

        tasks.sort(key=lambda t: self.calculate_task_urgency(t), reverse=True)

        profiles = list(
            UserProfile.objects.filter(is_available=True)
            .select_related('user')
            .prefetch_related('skills')
        )

        simulated_workload = {}
        for p in profiles:
            simulated_workload[p.user_id] = p.current_workload

        assigned_records = []
        unassigned_records = []

        with transaction.atomic():
            for task in tasks:
                best_candidate = None
                best_score = -1.0
                best_rationale = ""
                eligibility_failures = []

                for profile in profiles:
                    current_load = simulated_workload.get(profile.user_id, 0)
                    eval_res = self.evaluate_candidate(task, profile, current_load)

                    if eval_res['is_eligible']:
                        if eval_res['total_score'] > best_score:
                            best_score = eval_res['total_score']
                            best_candidate = profile
                            best_rationale = eval_res['rationale']
                    else:
                        eligibility_failures.append(eval_res['ineligibility_reason'])

                if best_candidate is not None:
                    task.assigned_to = best_candidate.user
                    task.status = 'IN_PROGRESS'
                    task.save(update_fields=['assigned_to', 'status', 'updated_at'])

                    simulated_workload[best_candidate.user_id] = simulated_workload.get(best_candidate.user_id, 0) + 1

                    log = AllocationLog.objects.create(
                        task=task,
                        assigned_user=best_candidate.user,
                        match_score=best_score,
                        reason=best_rationale,
                        allocation_type='AUTOMATIC'
                    )

                    assigned_records.append({
                        'task_id': task.id,
                        'task_title': task.title,
                        'priority': task.priority,
                        'assigned_user': best_candidate.user.get_full_name() or best_candidate.user.username,
                        'match_score': best_score,
                        'reason': best_rationale,
                    })
                else:
                    if not eligibility_failures:
                        fail_reason = "No team members exist in the system."
                    else:
                        fail_reason = f"No qualified resource available. Details: {'; '.join(eligibility_failures[:3])}"

                    unassigned_records.append({
                        'task_id': task.id,
                        'task_title': task.title,
                        'priority': task.priority,
                        'required_skill': task.required_skill.name,
                        'reason': fail_reason,
                    })

        assigned_count = len(assigned_records)
        unassigned_count = len(unassigned_records)
        msg = f"Algorithm executed successfully: {assigned_count} task(s) assigned, {unassigned_count} remained unassigned."

        return {
            'success': True,
            'total_tasks': len(tasks),
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
            'assignments': assigned_records,
            'unassigned': unassigned_records,
            'message': msg,
        }


def run_smart_allocation(task_queryset=None) -> dict:
    engine = SmartAllocationEngine()
    return engine.allocate_pending_tasks(task_queryset=task_queryset)
