import requests
import time

def measure_latency(url):
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    return latency, response.json()

url = "http://localhost:8000/trips/total"

# First request (without Redis cache)
latency1, response1 = measure_latency(url)
print(f"First request latency: {latency1:.2f} ms")

# Second request (with Redis cache)
latency2, response2 = measure_latency(url)
print(f"Second request latency: {latency2:.2f} ms")