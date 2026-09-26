def allocator_permissions(request):
    user = getattr(request, 'user', None)
    can_delete = False

    if user and user.is_authenticated:
        can_delete = (
            user.is_staff or
            user.is_superuser or
            (hasattr(user, 'profile') and user.profile.role in ['LEAD', 'ADMIN', 'MANAGER'])
        )

    return {
        'can_delete_tasks': can_delete,
    }
