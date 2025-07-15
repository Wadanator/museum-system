# Use Raspberry Pi compatible base image
FROM arm32v7/python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libasound2-dev \
    libpulse-dev \
    mpv \
    mosquitto \
    mosquitto-clients \
    openssh-server \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up SSH
RUN mkdir /var/run/sshd \
    && echo 'root:root' | chpasswd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/UsePAM yes/UsePAM no/' /etc/ssh/sshd_config

# Create working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure directories exist
RUN mkdir -p /app/logs/daily /app/audio /app/videos /app/scenes/room1 /app/scenes/room2 /app/Web /app/config

# Expose ports (5000 for web dashboard, 1883 for MQTT, 22 for SSH)
EXPOSE 5000 1883 22

# Start SSH and application
CMD ["/bin/bash", "-c", "service ssh start && /app/broker/start_broker.sh & python3 main.py"]