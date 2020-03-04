#!/bin/sh
# this script is used to boot a Docker container
source venv/bin/activate

while true; do
    venv/bin/flask db upgrade
    if [ "$?" = "0" ]; then
        break
    fi
    echo Deploy command failed, retrying in 5 secs...
    sleep 5
done

exec venv/bin/gunicorn -b :23381 --access-logfile - --error-logfile - sapspa:app
