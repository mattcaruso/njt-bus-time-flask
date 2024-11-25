#!/usr/bin/env bash

# Railway private networking takes 3 seconds to initialize. Delay start so the db can be found on railway.
# https://docs.railway.app/guides/private-networking#initialization-time
sleep 3
gunicorn wsgi:app --bind '[::]:8080' --log-level=debug --access-logfile '-' --error-logfile '-' --enable-stdio-inheritance --capture-output --workers=4 --threads=2 --max-requests 100 --max-requests-jitter 20