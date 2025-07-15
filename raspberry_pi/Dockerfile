# Multi-stage Dockerfile for Raspberry Pi 4 museum-system
FROM python:3.11-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio dependencies
    libasound2-dev \
    libpulse-dev \
    alsa-utils \
    pulseaudio \
    # Video dependencies
    mpv \
    # MQTT broker
    mosquitto \
    mosquitto-clients \
    # SSH server for remote development
    openssh-server \
    sudo \
    # Development tools
    git \
    nano \
    vim \
    htop \
    curl \
    wget \
    # GPIO dependencies
    python3-rpi.gpio \
    # Build tools for Python packages
    gcc \
    g++ \
    make \
    pkg-config \
    # Process management
    supervisor \
    # Networking tools
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Create app user with sudo privileges (for GPIO access)
RUN useradd -m -s /bin/bash -G sudo,audio,video,dialout,gpio museum && \
    echo "museum:museum" | chpasswd && \
    echo "museum ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Configure SSH
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' /etc/pam.d/sshd

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Python packages for development
RUN pip install --no-cache-dir \
    debugpy \
    pytest \
    black \
    flake8 \
    autopep8

# Create necessary directories
RUN mkdir -p /app/{audio,videos,scenes,logs/daily,config,Web,utils,broker,tools,service} && \
    chown -R museum:museum /app

# Copy project files
COPY --chown=museum:museum . /app/

# Make scripts executable
RUN chmod +x /app/broker/start_broker.sh && \
    chmod +x /app/tools/diagnostics/*.sh && \
    chmod +x /app/tools/DailyTasks/*.sh && \
    chmod +x /app/tools/Monitoring/*.sh && \
    chmod +x /app/tools/Blackscreen/*.bash

# Create supervisor configuration
COPY --chown=museum:museum <<EOF /etc/supervisor/conf.d/museum.conf
[supervisord]
nodaemon=true
user=root

[program:sshd]
command=/usr/sbin/sshd -D
autostart=true
autorestart=true
user=root

[program:mosquitto]
command=/app/broker/start_broker.sh
directory=/app/broker
autostart=true
autorestart=true
user=museum
stdout_logfile=/app/logs/mosquitto.log
stderr_logfile=/app/logs/mosquitto_error.log

[program:museum-app]
command=python /app/main.py
directory=/app
autostart=true
autorestart=true
user=museum
stdout_logfile=/app/logs/museum.log
stderr_logfile=/app/logs/museum-errors.log
environment=PYTHONPATH="/app"

[program:web-dashboard]
command=python /app/Web/web_dashboard.py
directory=/app
autostart=true
autorestart=true
user=museum
stdout_logfile=/app/logs/web_dashboard.log
stderr_logfile=/app/logs/web_dashboard_error.log
environment=PYTHONPATH="/app"
EOF

# Create startup script
COPY --chown=museum:museum <<EOF /app/start.sh
#!/bin/bash
set -e

# Wait for GPIO device
while [ ! -e /dev/gpiomem ]; do
    echo "Waiting for GPIO device..."
    sleep 1
done

# Start supervisor
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/museum.conf
EOF

RUN chmod +x /app/start.sh

# Expose ports
EXPOSE 22 1883 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Switch to museum user for final setup
USER museum

# Start the application
CMD ["/app/start.sh"]