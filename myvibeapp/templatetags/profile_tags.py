from django import template

register = template.Library()

@register.filter
def is_following(user_profile, target_profile):
    """Check if user_profile is following target_profile."""
    return user_profile.is_following(target_profile)