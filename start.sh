#!/bin/bash
pgrep redis-server || redis-server ~/Dropbox/configs/redis.conf
. ./venv/bin/activate && celery worker --autoreload --loglevel=info -A tasks -B
