#!/bin/bash
. ./venv/bin/activate && celery worker --autoreload --loglevel=info -A tasks -B
