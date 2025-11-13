#!/bin/bash
# Ensure logs directory exists and has proper permissions
mkdir -p /app/logs
chmod 755 /app/logs
# Run the application
exec "$@"