# events/context_processors.py
from django.utils import timezone
from .models import Event

def events_context(request):
    events = Event.objects.all().order_by('start_time').prefetch_related('interests')
    return {'events': events}