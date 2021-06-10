#!/bin/bash
# Taken from https://github.com/SeleniumHQ/docker-selenium#using-a-bash-script-to-wait-for-the-grid.

set -e

cmd="$@"

while ! curl -sSL "http://google-chrome:4444/wd/hub/status" 2>&1 \
        | jq -r '.value.ready' 2>&1 | grep "true" >/dev/null; do
    echo 'Waiting for Google Chrome to start...'
    sleep 1
done

exec $cmd
