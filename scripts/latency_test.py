import requests
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np


def measure_latency(url: str) -> Tuple[float, int]:
    """Measure the latency of a request and return both latency and status code."""
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to ms
    return latency, response.status_code


def test_endpoint(endpoint: str, iterations: int) -> Dict:
    """Test an endpoint multiple times and return detailed statistics."""
    print(f"\nTesting endpoint: {endpoint}")
    print(f"Number of iterations: {iterations}")
    print("-" * 50)

    latencies: List[float] = []
    status_codes: List[int] = []
    errors: List[str] = []

    for i in range(iterations):
        try:
            latency, status_code = measure_latency(endpoint)
            latencies.append(latency)
            status_codes.append(status_code)
            print(
                f"Iteration {i + 1}: Latency: {latency:.2f} ms, Status: {status_code}")
        except Exception as e:
            errors.append(f"Iteration {i + 1}: Error - {str(e)}")
            print(f"Iteration {i + 1}: Error - {str(e)}")

    if not latencies:
        return {
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "errors": errors,
            "success": False
        }

    stats = {
        "endpoint": endpoint,
        "timestamp": datetime.now().isoformat(),
        "iterations": iterations,
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "avg_latency": statistics.mean(latencies),
        "median_latency": statistics.median(latencies),
        "std_deviation": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "success_rate": (len(latencies) / iterations) * 100,
        "status_codes": dict(zip(*np.unique(status_codes, return_counts=True))),
        "errors": errors,
        "success": True
    }

    print("\nSummary:")
    print(f"Minimum Latency: {stats['min_latency']:.2f} ms")
    print(f"Maximum Latency: {stats['max_latency']:.2f} ms")
    print(f"Average Latency: {stats['avg_latency']:.2f} ms")
    print(f"Median Latency: {stats['median_latency']:.2f} ms")
    print(f"Standard Deviation: {stats['std_deviation']:.2f} ms")
    print(f"Success Rate: {stats['success_rate']:.1f}%")
    print(f"Status Codes: {stats['status_codes']}")
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"- {error}")

    return stats


def save_results(results: List[Dict], filename: str = None):
    """Save test results to a JSON file."""
    if filename is None:
        filename = f"latency_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {filename}")


if __name__ == "__main__":
    endpoints = {
        "1": "http://localhost:8000/trips/total",
        "2": "http://localhost:8000/trips/total/localities",
        "3": "http://localhost:8000/finance/revenue",
        "4": "http://localhost:8000/finance/revenue/localities"
    }

    print("Cacheable Endpoints Latency Test")
    print("=" * 50)
    print("\nAvailable endpoints:")
    for key, url in endpoints.items():
        print(f"{key}: {url}")

    results = []
    while True:
        choice = input(
            "\nEnter the number of the endpoint (or 'all' to test all, 'q' to quit): ")

        if choice.lower() == 'q':
            break
        elif choice.lower() == 'all':
            iterations = int(input("Enter the number of iterations: "))
            for url in endpoints.values():
                results.append(test_endpoint(url, iterations))
        elif choice in endpoints:
            iterations = int(input("Enter the number of iterations: "))
            results.append(test_endpoint(endpoints[choice], iterations))
        else:
            print("Invalid choice. Please try again.")

    if results:
        save = input(
            "\nDo you want to save the results to a JSON file? (y/n): ")
        if save.lower() == 'y':
            save_results(results)
