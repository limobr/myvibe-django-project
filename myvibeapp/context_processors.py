def active_menu(request):
    is_home_active = False
    is_account_active = False
    is_events_active = False
    is_discover_active = False
    is_notifications_active = False
    is_create_post_active = False

    path = request.path

    if path == '/home/':
        is_home_active = True
    elif path.startswith('/account/'):
        is_account_active = True
    elif path == '/events/':
        is_events_active = True
    elif path == '/discover/':
        is_discover_active = True
    elif path == '/notifications/':
        is_notifications_active = True
    elif path == '/create-post/':
        is_create_post_active = True

    return {
        'is_home_active': is_home_active,
        'is_account_active': is_account_active,
        'is_events_active': is_events_active,
        'is_discover_active': is_discover_active,
        'is_notifications_active': is_notifications_active,
        'is_create_post_active': is_create_post_active,
    }