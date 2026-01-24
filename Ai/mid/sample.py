import socket
import json
import time

# Create UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Controller IP and port
controller_ip = "192.168.1.10"
controller_port = 9000

# Send 100 packets at 1-second intervals
for i in range(100):
    metadata = {
        "sensor_id": "temp_1",
        "priority": 2,
        "queue_len": 1,
        "delay_est": 5
    }

    # Convert metadata to JSON and send
    try:
        s.sendto(json.dumps(metadata).encode(), (controller_ip, controller_port))
        print(f"[{i+1}] Packet generated and sent successfully to {controller_ip}:{controller_port}")
    except Exception as e:
        print(f"[{i+1}] Failed to send packet: {e}")

    # Wait 1 second before next packet
    time.sleep(1)

# Close socket after completion
s.close()
print("✅ All packets sent. Socket closed.")