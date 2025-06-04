import requests
import time
import json
import numpy as np
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"

# Cacheable endpoints to test
ENDPOINTS = [
    "/api/v1/trips/total",
    "/api/v1/finance/revenue",
    "/api/v1/users/active/count"
]


def test_endpoint(endpoint: str, iterations: int = 5) -> Tuple[float, float, float]:
    """Test an endpoint multiple times and return statistics."""
    times = []

    for i in range(iterations):
        start_time = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}")
        end_time = time.time()

        if response.status_code == 200:
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            times.append(latency)
            print(f"Request {i+1}/{iterations} to {endpoint}: {latency:.2f}ms")
        else:
            print(
                f"Error on request {i+1}/{iterations} to {endpoint}: {response.status_code}")

    if times:
        return np.mean(times), np.min(times), np.max(times)
    return 0, 0, 0


def main():
    print("\n=== Cacheable Endpoints Latency Test ===\n")

    results = {}
    for endpoint in ENDPOINTS:
        print(f"\nTesting {endpoint}...")
        mean, min_time, max_time = test_endpoint(endpoint)
        results[endpoint] = {
            "mean_latency_ms": round(mean, 2),
            "min_latency_ms": round(min_time, 2),
            "max_latency_ms": round(max_time, 2)
        }

    print("\n=== Results ===")
    print(json.dumps(results, indent=2))

    # Save results to file
    with open("latency_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to latency_results.json")


if __name__ == "__main__":
    main()
