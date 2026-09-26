from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task, UserProfile, Skill


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'priority',
            'required_skill',
            'deadline',
            'estimated_hours',
            'assigned_to',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Develop REST API for User Authentication',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Provide comprehensive context and acceptance criteria...',
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'required_skill': forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 200,
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-select',
                'help_text': 'Leave unassigned for the smart algorithm to match automatically',
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = "-- Unassigned (Auto Allocate) --"
        if 'assigned_to' in self.fields:
            self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).select_related('profile')
            self.fields['assigned_to'].label_from_instance = (
                lambda u: f"{u.get_full_name() or u.username} ({u.profile.get_role_display() if hasattr(u, 'profile') else 'Member'})"
            )


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'skills', 'max_capacity', 'is_available']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'skills': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 6,
            }),
            'max_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20,
            }),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'category', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Python Backend, React UI, Kubernetes...',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of this skill...',
            }),
        }
