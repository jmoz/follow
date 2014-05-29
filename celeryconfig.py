import os
from datetime import timedelta

# to run, ensure redis-server is running then run celery worker --autoreload --loglevel=info -A tasks -B

BROKER_URL = os.environ['BROKER_URL']
CELERY_RESULT_BACKEND = os.environ['CELERY_RESULT_BACKEND']

CELERYBEAT_SCHEDULE = {
    'fav-every-2-hours': {
        'task': 'tasks.fav',
        'schedule': timedelta(hours=2),
        'args': (os.environ['KEYWORDS'].split(','), 50, 3, 3)
    },
}

CELERY_TIMEZONE = 'Europe/London'
