import requests
import time

def measure_latency(url):
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    return latency, response.json()

def test_endpoint(endpoint, iterations):
    print(f"Testing endpoint: {endpoint} for {iterations} iterations")
    for i in range(iterations):
        latency, response = measure_latency(endpoint)
        print(f"Iteration {i + 1}: Latency: {latency:.2f} ms")

if __name__ == "__main__":
    endpoints = {
        "1": "http://localhost:8000/trips/total",
        "2": "http://localhost:8000/finance/revenue"
    }

    print("Choose an endpoint to test:")
    for key, url in endpoints.items():
        print(f"{key}: {url}")

    choice = input("Enter the number of the endpoint: ")
    if choice in endpoints:
        iterations = int(input("Enter the number of iterations: "))
        test_endpoint(endpoints[choice], iterations)
    else:
        print("Invalid choice. Exiting.")