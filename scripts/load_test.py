import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List

BASE_URL = "http://localhost:8000"

# Endpoints to test
ENDPOINTS = [
    "/api/v1/trips/total",
    "/api/v1/finance/revenue",
    "/api/v1/users/active/count"
]


def run_ab_test(endpoint: str, concurrency: int = 10, requests: int = 100) -> Dict:
    """Run Apache Benchmark test on an endpoint."""
    url = f"{BASE_URL}{endpoint}"
    cmd = [
        "ab",
        "-n", str(requests),
        "-c", str(concurrency),
        "-g", f"ab_results_{endpoint.replace('/', '_')}.dat",
        url
    ]

    print(
        f"\nTesting {endpoint} with {concurrency} concurrent users, {requests} requests...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running ab test: {result.stderr}")
        return {}

    # Parse ab output
    output = result.stdout
    stats = {}

    # Extract key metrics
    for line in output.split('\n'):
        if "Requests per second:" in line:
            stats["requests_per_second"] = float(line.split()[0])
        elif "Time per request:" in line and "mean" in line:
            stats["time_per_request_ms"] = float(line.split()[0])
        elif "Transfer rate:" in line:
            stats["transfer_rate_kbps"] = float(line.split()[0])
        elif "Failed requests:" in line:
            stats["failed_requests"] = int(line.split()[0])

    return stats


def main():
    print("\n=== Load Testing with Apache Benchmark ===\n")

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }

    for endpoint in ENDPOINTS:
        stats = run_ab_test(endpoint)
        if stats:
            results["tests"][endpoint] = stats

    print("\n=== Results ===")
    print(json.dumps(results, indent=2))

    # Save results to file
    with open("load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to load_test_results.json")


if __name__ == "__main__":
    main()
