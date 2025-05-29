import requests
import time

def measure_latency(url):
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    return latency, response.json()

urls = [
    "http://localhost:8000/users/count",
    "http://localhost:8000/users/active/count",
    "http://localhost:8000/users/latest"
]

for url in urls:
    latency, response = measure_latency(url)
    print(f"Endpoint: {url}")
    print(f"Latency: {latency:.2f} ms")
    print(f"Response: {response}")
    print("-" * 50)