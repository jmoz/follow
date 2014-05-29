#!/bin/bash
pgrep redis-server || redis-server ~/Dropbox/configs/redis.conf
source /usr/local/bin/virtualenvwrapper.sh
workon follow && celery worker --autoreload --loglevel=info -A tasks -B
