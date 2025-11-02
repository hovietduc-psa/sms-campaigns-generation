"""
Load testing for SMS Campaign Generation API.

Tests cover performance under various load conditions including
concurrent requests, sustained load, and stress testing.
"""

import asyncio
import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import json
import httpx

from src.core.config import get_settings


@pytest.mark.performance
@pytest.mark.slow
class TestLoadPerformance:
    """Load performance tests."""

    @pytest.fixture
    def api_base_url(self):
        """Get API base URL for testing."""
        return "http://localhost:8000"

    @pytest.fixture
    def test_campaigns(self):
        """Sample campaign descriptions for load testing."""
        return [
            {
                "campaignDescription": "Create a welcome series for new subscribers with 3 messages over 7 days"
            },
            {
                "campaignDescription": "Design an abandoned cart recovery campaign with personalized offers and urgency tactics"
            },
            {
                "campaignDescription": "Build a weekly promotional campaign for segment-based product recommendations"
            },
            {
                "campaignDescription": "Develop a birthday celebration campaign with special discounts and personalized messages"
            },
            {
                "campaignDescription": "Create a re-engagement campaign for inactive users with win-back offers"
            }
        ]

    def get_performance_metrics(self, response_times: List[float]) -> Dict[str, Any]:
        """Calculate performance metrics from response times."""
        if not response_times:
            return {}

        return {
            "total_requests": len(response_times),
            "avg_response_time_ms": statistics.mean(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": self.percentile(response_times, 95),
            "p99_response_time_ms": self.percentile(response_times, 99),
            "requests_per_second": len(response_times) / (max(response_times) / 1000) if max(response_times) > 0 else 0
        }

    def percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))

    def make_single_request(self, client: httpx.Client, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """Make a single API request and return metrics."""
        start_time = time.time()
        try:
            response = client.post(
                "/api/v1/generateFlow",
                json=campaign,
                timeout=30.0
            )
            response_time = (time.time() - start_time) * 1000

            return {
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": response.status_code == 200,
                "error": None if response.status_code == 200 else response.text
            }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status_code": 0,
                "response_time_ms": response_time,
                "success": False,
                "error": str(e)
            }

    def test_baseline_performance(self, api_base_url, test_campaigns):
        """Test baseline performance with single requests."""
        print("\n=== Baseline Performance Test ===")

        with httpx.Client(base_url=api_base_url) as client:
            response_times = []
            success_count = 0

            for i, campaign in enumerate(test_campaigns):
                print(f"Making request {i+1}/{len(test_campaigns)}...")

                result = self.make_single_request(client, campaign)
                response_times.append(result["response_time_ms"])

                if result["success"]:
                    success_count += 1
                    print(f"  ✓ Success in {result['response_time_ms']:.2f}ms")
                else:
                    print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

        metrics = self.get_performance_metrics(response_times)
        success_rate = (success_count / len(test_campaigns)) * 100

        print(f"Results:")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Response Time: {metrics['avg_response_time_ms']:.2f}ms")
        print(f"  95th Percentile: {metrics['p95_response_time_ms']:.2f}ms")
        print(f"  Max Response Time: {metrics['max_response_time_ms']:.2f}ms")

        # Performance assertions
        assert success_rate >= 80, f"Success rate too low: {success_rate}%"
        assert metrics['avg_response_time_ms'] < 20000, f"Average response time too high: {metrics['avg_response_time_ms']}ms"
        assert metrics['p95_response_time_ms'] < 30000, f"95th percentile too high: {metrics['p95_response_time_ms']}ms"

    def test_concurrent_load(self, api_base_url, test_campaigns):
        """Test performance under concurrent load."""
        print("\n=== Concurrent Load Test ===")

        concurrent_users = 10
        requests_per_user = 5
        total_requests = concurrent_users * requests_per_user

        print(f"Simulating {concurrent_users} concurrent users, {requests_per_user} requests each")

        def user_session():
            """Simulate a user session with multiple requests."""
            with httpx.Client(base_url=api_base_url) as client:
                session_results = []
                for i in range(requests_per_user):
                    campaign = test_campaigns[i % len(test_campaigns)]
                    result = self.make_single_request(client, campaign)
                    session_results.append(result)
                    # Small delay between requests
                    time.sleep(0.1)
                return session_results

        # Run concurrent user sessions
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_session) for _ in range(concurrent_users)]
            all_results = []

            for future in as_completed(futures):
                try:
                    session_results = future.result(timeout=60)
                    all_results.extend(session_results)
                except Exception as e:
                    print(f"Session failed: {e}")

        # Analyze results
        response_times = [r["response_time_ms"] for r in all_results]
        success_count = sum(1 for r in all_results if r["success"])
        metrics = self.get_performance_metrics(response_times)
        success_rate = (success_count / total_requests) * 100

        print(f"Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful Requests: {success_count}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Response Time: {metrics['avg_response_time_ms']:.2f}ms")
        print(f"  95th Percentile: {metrics['p95_response_time_ms']:.2f}ms")
        print(f"  Requests per Second: {metrics['requests_per_second']:.2f}")

        # Performance assertions
        assert success_rate >= 75, f"Success rate too low under load: {success_rate}%"
        assert metrics['avg_response_time_ms'] < 25000, f"Average response time too high under load: {metrics['avg_response_time_ms']}ms"
        assert metrics['requests_per_second'] > 0.5, f"Requests per second too low: {metrics['requests_per_second']}"

    def test_sustained_load(self, api_base_url, test_campaigns):
        """Test performance under sustained load."""
        print("\n=== Sustained Load Test ===")

        duration_seconds = 60  # 1 minute test
        target_rps = 2  # 2 requests per second
        request_interval = 1.0 / target_rps

        print(f"Running sustained load for {duration_seconds} seconds at {target_rps} RPS")

        with httpx.Client(base_url=api_base_url) as client:
            start_time = time.time()
            results = []
            request_count = 0

            while time.time() - start_time < duration_seconds:
                request_start = time.time()
                campaign = test_campaigns[request_count % len(test_campaigns)]

                result = self.make_single_request(client, campaign)
                results.append(result)
                request_count += 1

                # Maintain target RPS
                elapsed = time.time() - request_start
                sleep_time = max(0, request_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            actual_duration = time.time() - start_time
            actual_rps = request_count / actual_duration

        # Analyze results
        response_times = [r["response_time_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        metrics = self.get_performance_metrics(response_times)
        success_rate = (success_count / len(results)) * 100

        print(f"Results:")
        print(f"  Test Duration: {actual_duration:.2f}s")
        print(f"  Total Requests: {request_count}")
        print(f"  Actual RPS: {actual_rps:.2f}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Response Time: {metrics['avg_response_time_ms']:.2f}ms")
        print(f"  Response Time Trend: {self.calculate_trend(response_times):.2f}ms/request")

        # Performance assertions
        assert success_rate >= 80, f"Success rate too low during sustained load: {success_rate}%"
        assert actual_rps >= target_rps * 0.8, f"Actual RPS too low: {actual_rps} < {target_rps * 0.8}"

        # Check for performance degradation
        trend = self.calculate_trend(response_times)
        if trend > 100:  # Response times increasing by more than 100ms per request
            print(f"WARNING: Performance degradation detected (trend: {trend:.2f}ms/request)")

    def test_stress_test(self, api_base_url, test_campaigns):
        """Test system behavior under extreme stress."""
        print("\n=== Stress Test ===")

        max_concurrent = 50  # Maximum concurrent users
        ramp_up_time = 30  # Seconds to ramp up to max users
        test_duration = 60  # Total test duration

        print(f"Stress test: ramping to {max_concurrent} users over {ramp_up_time}s, total {test_duration}s")

        results = []
        user_threads = []
        stop_time = time.time() + test_duration

        def stress_user(user_id: int):
            """Stress test user thread."""
            with httpx.Client(base_url=api_base_url) as client:
                while time.time() < stop_time:
                    campaign = test_campaigns[user_id % len(test_campaigns)]
                    result = self.make_single_request(client, campaign)
                    result["user_id"] = user_id
                    results.append(result)

                    # Variable delay to simulate realistic usage
                    time.sleep(0.5 + (user_id % 5) * 0.1)

        # Ramp up users gradually
        users_started = 0
        ramp_interval = ramp_up_time / max_concurrent

        while users_started < max_concurrent and time.time() < stop_time:
            thread = threading.Thread(target=stress_user, args=(users_started,))
            thread.daemon = True
            thread.start()
            user_threads.append(thread)
            users_started += 1
            time.sleep(ramp_interval)

        # Wait for test completion
        for thread in user_threads:
            thread.join(timeout=5)

        # Analyze results
        if results:
            response_times = [r["response_time_ms"] for r in results]
            success_count = sum(1 for r in results if r["success"])
            metrics = self.get_performance_metrics(response_times)
            success_rate = (success_count / len(results)) * 100

            print(f"Results:")
            print(f"  Total Requests: {len(results)}")
            print(f"  Concurrent Users: {users_started}")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Average Response Time: {metrics['avg_response_time_ms']:.2f}ms")
            print(f"  95th Percentile: {metrics['p95_response_time_ms']:.2f}ms")
            print(f"  Max Response Time: {metrics['max_response_time_ms']:.2f}ms")

            # Stress test assertions (more lenient)
            assert len(results) > 0, "No requests completed during stress test"
            assert success_rate >= 50, f"Success rate too low under stress: {success_rate}%"
        else:
            pytest.skip("No results collected during stress test")

    def test_batch_performance(self, api_base_url, test_campaigns):
        """Test batch request performance."""
        print("\n=== Batch Performance Test ===")

        batch_sizes = [2, 5, 10]  # Different batch sizes to test

        with httpx.Client(base_url=api_base_url) as client:
            for batch_size in batch_sizes:
                print(f"Testing batch size: {batch_size}")

                # Create batch request
                batch_campaigns = test_campaigns[:batch_size]

                start_time = time.time()
                try:
                    response = client.post(
                        "/api/v1/generateFlow/batch",
                        json=batch_campaigns,
                        timeout=60.0
                    )
                    response_time = (time.time() - start_time) * 1000

                    if response.status_code == 200:
                        data = response.json()
                        success_count = data.get("successful_generations", 0)
                        total_time_per_campaign = response_time / batch_size

                        print(f"  ✓ Batch completed in {response_time:.2f}ms")
                        print(f"  ✓ {success_count}/{batch_size} campaigns successful")
                        print(f"  ✓ Average time per campaign: {total_time_per_campaign:.2f}ms")

                        # Batch performance assertions
                        assert response_time < 60000, f"Batch request too slow: {response_time}ms"
                        assert success_count >= batch_size * 0.8, f"Too many failed campaigns in batch: {success_count}/{batch_size}"
                    else:
                        print(f"  ✗ Batch failed: {response.status_code} - {response.text}")

                except Exception as e:
                    print(f"  ✗ Batch error: {e}")

    def test_endurance_test(self, api_base_url, test_campaigns):
        """Test system endurance over extended period."""
        print("\n=== Endurance Test ===")

        endurance_duration = 300  # 5 minutes
        low_rps = 1  # Low sustained load

        print(f"Running endurance test for {endurance_duration/60:.1f} minutes at {low_rps} RPS")

        with httpx.Client(base_url=api_base_url) as client:
            start_time = time.time()
            results = []
            request_count = 0

            while time.time() - start_time < endurance_duration:
                campaign = test_campaigns[request_count % len(test_campaigns)]

                result = self.make_single_request(client, campaign)
                results.append(result)
                request_count += 1

                # Low rate pacing
                time.sleep(1.0 / low_rps)

        # Analyze results
        response_times = [r["response_time_ms"] for r in results]
        success_count = sum(1 for r in results if r["success"])
        metrics = self.get_performance_metrics(response_times)
        success_rate = (success_count / len(results)) * 100

        print(f"Results:")
        print(f"  Test Duration: {endurance_duration/60:.1f} minutes")
        print(f"  Total Requests: {request_count}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Response Time: {metrics['avg_response_time_ms']:.2f}ms")
        print(f"  Performance Stability: {self.calculate_stability(response_times):.2f}")

        # Check for memory leaks or performance degradation
        first_quarter = response_times[:len(response_times)//4]
        last_quarter = response_times[-len(response_times)//4:]

        first_avg = statistics.mean(first_quarter) if first_quarter else 0
        last_avg = statistics.mean(last_quarter) if last_quarter else 0
        degradation = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        print(f"  Performance Degradation: {degradation:.1f}%")

        # Endurance test assertions
        assert success_rate >= 90, f"Success rate too low during endurance test: {success_rate}%"
        assert abs(degradation) < 50, f"Performance degradation too high: {degradation}%"

    def calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend of values (change per item)."""
        if len(values) < 2:
            return 0

        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return slope

    def calculate_stability(self, values: List[float]) -> float:
        """Calculate stability (inverse of coefficient of variation)."""
        if not values or len(values) < 2:
            return 1.0

        mean = statistics.mean(values)
        if mean == 0:
            return 0

        std_dev = statistics.stdev(values)
        cv = std_dev / mean  # Coefficient of variation
        stability = 1 / (1 + cv)  # Convert to stability score (0-1)
        return stability


@pytest.mark.performance
class TestResourceUsage:
    """Resource usage monitoring during performance tests."""

    def test_memory_usage_during_load(self, api_base_url, test_campaigns):
        """Test memory usage during load."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"\nInitial memory usage: {initial_memory:.2f} MB")

        # Make several requests
        with httpx.Client(base_url=api_base_url) as client:
            for i in range(20):
                campaign = test_campaigns[i % len(test_campaigns)]
                client.post("/api/v1/generateFlow", json=campaign, timeout=30.0)

                if i % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory
                    print(f"  Request {i+1}: Memory usage {current_memory:.2f} MB (+{memory_increase:.2f} MB)")

        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print(f"Final memory usage: {final_memory:.2f} MB")
        print(f"Total memory increase: {total_increase:.2f} MB")

        # Memory usage should not increase dramatically
        assert total_increase < 100, f"Memory leak detected: {total_increase:.2f} MB increase"

    def test_cpu_usage_during_load(self, api_base_url, test_campaigns):
        """Test CPU usage during concurrent load."""
        import psutil
        import threading
        import time

        process = psutil.Process()
        cpu_samples = []

        def monitor_cpu(duration_seconds):
            """Monitor CPU usage."""
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                cpu_percent = process.cpu_percent()
                cpu_samples.append(cpu_percent)
                time.sleep(0.5)

        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu, args=(30,))
        monitor_thread.daemon = True
        monitor_thread.start()

        # Generate load
        with httpx.Client(base_url=api_base_url) as client:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for _ in range(25):
                    campaign = test_campaigns[0]
                    future = executor.submit(client.post, "/api/v1/generateFlow", json=campaign, timeout=30.0)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass

        monitor_thread.join(timeout=5)

        if cpu_samples:
            avg_cpu = statistics.mean(cpu_samples)
            max_cpu = max(cpu_samples)

            print(f"Average CPU usage: {avg_cpu:.1f}%")
            print(f"Peak CPU usage: {max_cpu:.1f}%")

            # CPU usage should be reasonable
            assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"
            assert max_cpu < 95, f"Peak CPU usage too high: {max_cpu:.1f}%"