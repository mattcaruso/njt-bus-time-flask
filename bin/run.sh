#!/usr/bin/env bash

# Railway private networking takes 3 seconds to initialize. Delay start so the db can be found on railway.
# https://docs.railway.app/guides/private-networking#initialization-time
sleep 3
gunicorn wsgi:app --bind '[::]:8080' --log-level=debug --workers=4 --threads=2