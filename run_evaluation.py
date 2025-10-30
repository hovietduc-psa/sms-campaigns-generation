#!/usr/bin/env python3
"""
Evaluation script to test all test cases and analyze results.
"""
import json
import requests
import time
from datetime import datetime

def load_test_cases():
    """Load test cases from JSON file."""
    with open('test_case.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def run_single_test(case_name, description):
    """Run a single campaign generation test."""
    url = "http://localhost:8000/api/v1/campaigns/generate"

    payload = {
        "merchant_id": f"test_merchant_{case_name}",
        "description": description,
        "settings": {
            "include_templates": False,
            "validate_only": False
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "test-api-key"
    }

    print(f"\n{'='*60}")
    print(f"TEST CASE: {case_name}")
    print(f"{'='*60}")
    print(f"DESCRIPTION:\n{description[:200]}...")

    start_time = time.time()

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        end_time = time.time()

        result = {
            "case_name": case_name,
            "description": description,
            "status_code": response.status_code,
            "response_time_ms": round((end_time - start_time) * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }

        if response.status_code == 201:
            response_data = response.json()
            campaign_data = response_data.get("campaign_data", {})
            campaign_json = campaign_data.get("campaign_json", {})
            steps = campaign_json.get("steps", [])

            result.update({
                "success": True,
                "campaign_id": response_data.get("campaign_id"),
                "total_steps": len(steps),
                "step_types": [step.get("type") for step in steps],
                "validation": campaign_data.get("validation", {}),
                "metadata": campaign_data.get("generation_metadata", {})
            })

            print(f"\nSUCCESS: Campaign generated")
            print(f"   Campaign ID: {result['campaign_id']}")
            print(f"   Response Time: {result['response_time_ms']}ms")
            print(f"   Total Steps: {result['total_steps']}")
            print(f"   Step Types: {result['step_types']}")

            # Validation analysis
            validation = result['validation']
            if validation.get("is_valid", False):
                quality_score = validation.get("overall_score", 0)
                quality_grade = validation.get("quality_grade", "N/A")
                issues = validation.get("issues", [])
                warnings = validation.get("warnings", [])

                print(f"\n📊 VALIDATION RESULTS:")
                print(f"   Quality Grade: {quality_grade}")
                print(f"   Quality Score: {quality_score}/100")
                print(f"   Issues: {len(issues)}")
                print(f"   Warnings: {len(warnings)}")

                if issues:
                    print(f"   Issue Details:")
                    for issue in issues[:3]:  # Show first 3 issues
                        print(f"     - {issue}")

                # Step analysis
                print(f"\n🔍 STEP ANALYSIS:")
                step_count = {}
                for step_type in result['step_types']:
                    step_count[step_type] = step_count.get(step_type, 0) + 1

                for step_type, count in sorted(step_count.items()):
                    print(f"   {step_type}: {count}")

                # Check for required elements based on test case
                print(f"\n🎯 REQUIREMENT ANALYSIS:")
                if "Schedule" in description:
                    has_schedule = any(step.get("type") == "schedule" for step in steps)
                    print(f"   Schedule Node: {'✅' if has_schedule else '❌'}")

                if "Target" in description:
                    has_segment = any(step.get("type") in ["segment", "property"] for step in steps)
                    print(f"   Target Audience: {'✅' if has_segment else '❌'}")

                if "Reply" in description:
                    has_reply_events = any(
                        "events" in step and
                        any(event.get("type") == "reply" for event in step.get("events", []))
                        for step in steps
                    )
                    print(f"   Reply Events: {'✅' if has_reply_events else '❌'}")

        else:
            result["success"] = False
            result["error"] = response.text
            print(f"\n❌ FAILED: Status {response.status_code}")
            print(f"   Error: {response.text}")

        return result

    except Exception as e:
        print(f"\n💥 EXCEPTION: {str(e)}")
        return {
            "case_name": case_name,
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main evaluation function."""
    print("STARTING SOLUTION EVALUATION")
    print("=" * 80)

    # Check API health
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ API health check failed!")
            return
        print("API is healthy and ready")
    except Exception as e:
        print(f"Cannot connect to API: {e}")
        return

    # Load and run test cases
    try:
        test_cases = load_test_cases()
        print(f"\n📋 Found {len(test_cases)} test cases")
    except Exception as e:
        print(f"❌ Failed to load test cases: {e}")
        return

    results = []
    for case_name, description in test_cases.items():
        result = run_single_test(case_name, description)
        results.append(result)
        time.sleep(2)  # Brief pause between tests

    # Generate summary
    print(f"\n{'='*80}")
    print("📊 EVALUATION SUMMARY")
    print(f"{'='*80}")

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - successful_tests

    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Success Rate: {(successful_tests/total_tests*100):.1f}%")

    if successful_tests > 0:
        avg_response_time = sum(r.get("response_time_ms", 0) for r in results if r.get("success")) / successful_tests
        avg_steps = sum(r.get("total_steps", 0) for r in results if r.get("success")) / successful_tests

        print(f"\nPerformance Metrics:")
        print(f"   Average Response Time: {avg_response_time:.0f}ms")
        print(f"   Average Steps Generated: {avg_steps:.1f}")

        # Quality analysis
        grades = [r.get("validation", {}).get("quality_grade", "N/A") for r in results if r.get("success")]
        if grades:
            grade_dist = {grade: grades.count(grade) for grade in set(grades)}
            print(f"\nQuality Grade Distribution:")
            for grade, count in sorted(grade_dist.items()):
                print(f"   Grade {grade}: {count} campaigns")

    # Save results
    results_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed results saved to: {results_file}")
    print(f"\n🏁 EVALUATION COMPLETE!")

if __name__ == "__main__":
    main()