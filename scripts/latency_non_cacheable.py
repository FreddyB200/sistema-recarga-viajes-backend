import requests
import time

def measure_latency(url):
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    return latency, response.json()

def test_endpoints(urls, iterations):
    for url in urls:
        print(f"Testing endpoint: {url} for {iterations} iterations")
        for i in range(iterations):
            latency, response = measure_latency(url)
            print(f"Iteration {i + 1}: Latency: {latency:.2f} ms")
            print(f"Response: {response}")
            print("-" * 50)

if __name__ == "__main__":
    urls = [
        "http://localhost:8000/users/count",
        "http://localhost:8000/users/active/count",
        "http://localhost:8000/users/latest"
    ]

    iterations = int(input("Enter the number of iterations: "))
    test_endpoints(urls, iterations)