#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import time
import argparse

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if args.subscribe:
        print(f"Subscribing to topic: {args.topic}")
        client.subscribe(args.topic)

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} = {msg.payload.decode()}")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published")

# Parse arguments
parser = argparse.ArgumentParser(description='MQTT Publisher/Subscriber for testing')
parser.add_argument('-b', '--broker', default='localhost', help='MQTT broker address')
parser.add_argument('-p', '--port', type=int, default=1883, help='MQTT broker port')
parser.add_argument('-t', '--topic', default='test/topic', help='MQTT topic')
parser.add_argument('-m', '--message', help='Message to publish')
parser.add_argument('-s', '--subscribe', action='store_true', help='Act as subscriber')

args = parser.parse_args()

# Setup client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_publish = on_publish

# Connect
client.connect(args.broker, args.port, 60)

if args.subscribe:
    # Run as subscriber
    print(f"Running as subscriber to topic: {args.topic}")
    client.loop_forever()
else:
    # Run as publisher
    message = args.message if args.message else "Test message"
    print(f"Publishing to {args.topic}: {message}")
    client.publish(args.topic, message)
    time.sleep(1)  # Wait for message to be published
    client.disconnect()
