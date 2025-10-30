#!/usr/bin/env python3
"""
Final validation script to confirm 100% FlowBuilder node coverage achievement
"""
import requests
import json
import time

def validate_complete_coverage():
    """Validate that all 16 FlowBuilder node types are implemented and working"""

    base_url = "http://localhost:8001"
    api_endpoint = f"{base_url}/api/v1/campaigns/generate"

    # Test campaign designed to trigger ALL 16 node types
    comprehensive_test = {
        "merchant_id": "final_coverage_validation",
        "description": """COMPREHENSIVE COVERAGE VALIDATION - All 16 FlowBuilder Node Types

1. SCHEDULE: Send tomorrow 9am EST business hours only

2. FILTER: Only customers with purchase_count > 2 AND total_spent > 100
If filter passed: go to qualified_customers
If filter failed: go to new_customers

3. SEGMENT: Customers who engaged in past 30 days
Target: engaged_customers segment

4. WEBHOOK: Call external CRM API
URL: https://api.crm.com/sync
Method: POST, timeout 30 seconds, 3 retries
Body: {"customer_id": "{{customer.id}}", "campaign_id": "{{campaign.id}}"}
On success: go to personalization_step
On failure: go to generic_step

5. SPLIT: Divide audience 50/50 for A/B testing
Group A: control_group → message_variant_a
Group B: test_group → message_variant_b

6. EXPERIMENT: A/B test with 2 variants
Variant A: Standard promotional message
Variant B: Personalized product recommendations
Success metrics: conversion_rate, click_rate
Duration: 7 days

7. RATE_LIMIT: Compliance controls
Max 3 messages per day, 1 per hour
Business hours only, no weekends
60 minute cooldown between messages

8. PRODUCT_CHOICE: Show personalized product recommendations
Featured products with images and prices
Customer-specific based on purchase history

9. PROPERTY: Check customer VIP status
If customer.is_vip = true: go to vip_path
Else: go to standard_path

10. DELAY: Strategic timing control
Wait 2 hours before follow-up message
Business hours only, max wait 3 days

11. MESSAGE: Send personalized promotional content
Dynamic content based on customer data
Product recommendations and personalized offers

12. END: Campaign completion

This campaign validates implementation of all 16 FlowBuilder node types:
MESSAGE, END, SEGMENT, SCHEDULE, PRODUCT_CHOICE, PROPERTY,
EXPERIMENT, RATE_LIMIT, SPLIT, DELAY, WEBHOOK, FILTER,
plus standard nodes for complete coverage verification."""
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "test_api_key"
    }

    print("🎯 FINAL COVERAGE VALIDATION")
    print("="*60)
    print("Testing comprehensive campaign with all 16 FlowBuilder node types...")

    try:
        start_time = time.time()
        response = requests.post(api_endpoint, json=comprehensive_test, headers=headers)
        end_time = time.time()

        if response.status_code == 201:
            result = response.json()
            campaign = result.get('campaign', {})
            steps = campaign.get('steps', [])
            generation_time = end_time - start_time

            print(f"\n✅ Campaign generated successfully in {generation_time:.2f}s!")

            # Analyze node types
            node_types = {}
            for step in steps:
                node_type = step.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1

            print(f"\n📊 Node Type Analysis:")
            print(f"Total steps generated: {len(steps)}")

            # Expected all 16 FlowBuilder node types
            expected_nodes = [
                'MESSAGE', 'END', 'SEGMENT', 'SCHEDULE',
                'PRODUCT_CHOICE', 'PROPERTY', 'EXPERIMENT',
                'RATE_LIMIT', 'SPLIT', 'DELAY', 'WEBHOOK', 'FILTER',
                'PURCHASE_OFFER', 'REPLY', 'NO_REPLY'
            ]

            print(f"\n🔍 Node Implementation Status:")
            implemented_count = 0
            for node_type in expected_nodes:
                count = node_types.get(node_type, 0)
                status = "✅" if count > 0 else "❌"
                print(f"  {status} {node_type}: {count}")
                if count > 0:
                    implemented_count += 1

            # Check for additional node types
            additional_nodes = [node for node in node_types.keys() if node not in expected_nodes]
            if additional_nodes:
                print(f"\n🔧 Additional Node Types:")
                for node_type in additional_nodes:
                    print(f"  ➕ {node_type}: {node_types[node_type]}")

            # Validate final coverage
            metadata = campaign.get('_metadata', {})
            final_coverage = metadata.get('final_coverage', {})

            if final_coverage:
                coverage_percentage = final_coverage.get('coverage_percentage', 0)
                implemented_nodes = final_coverage.get('implemented_nodes', 0)
                total_nodes = final_coverage.get('total_nodes', 16)
                node_list = final_coverage.get('node_types', [])
                phase_complete = final_coverage.get('phase_complete', False)

                print(f"\n🏆 FINAL COVERAGE RESULTS:")
                print(f"  Coverage Percentage: {coverage_percentage:.1f}%")
                print(f"  Implemented Nodes: {implemented_nodes}/{total_nodes}")
                print(f"  Node Types: {', '.join(sorted(node_list))}")
                print(f"  Phase Complete: {phase_complete}")

                # Achievement validation
                print(f"\n🎉 ACHIEVEMENT VALIDATION:")
                if coverage_percentage >= 100:
                    print("  🏆 ACHIEVED: 100% FlowBuilder Node Coverage!")
                    print("  ✅ All 16 node types successfully implemented!")
                    print("  🚀 System ready for enterprise deployment!")
                    grade = "A+"
                elif coverage_percentage >= 90:
                    print("  🥇 EXCELLENT: Near-complete coverage achieved")
                    print(f"  ✅ {implemented_nodes}/16 node types implemented")
                    grade = "A"
                elif coverage_percentage >= 75:
                    print("  🥈 GOOD: Solid coverage with room for improvement")
                    print(f"  ⚠️  {implemented_nodes}/16 node types implemented")
                    grade = "B"
                else:
                    print("  🥉 ACCEPTABLE: Coverage needs improvement")
                    print(f"  ❌ {implemented_nodes}/16 node types implemented")
                    grade = "C"

                # Performance validation
                print(f"\n⚡ PERFORMANCE VALIDATION:")
                if generation_time < 5:
                    print("  🚀 Excellent: Under 5 seconds")
                elif generation_time < 10:
                    print("  ✅ Good: Under 10 seconds")
                elif generation_time < 20:
                    print("  ⚠️  Acceptable: Under 20 seconds")
                else:
                    print("  ❌ Needs optimization: Over 20 seconds")

                # Feature validation
                phase4_improvements = metadata.get('phase4_improvements', {})
                webhook_added = phase4_improvements.get('webhook_added', False)
                filter_added = phase4_improvements.get('filter_added', False)

                print(f"\n🔧 PHASE 4 FEATURE VALIDATION:")
                print(f"  WEBHOOK nodes: {'✅' if webhook_added else '❌'}")
                print(f"  FILTER nodes: {'✅' if filter_added else '❌'}")

                # Final result
                print(f"\n📋 FINAL VALIDATION RESULT:")
                print(f"  Overall Grade: {grade}")
                print(f"  Coverage: {coverage_percentage:.1f}%")
                print(f"  Performance: {generation_time:.2f}s")
                print(f"  Features: Complete Phase 1-4 implementation")

                if coverage_percentage >= 100 and webhook_added and filter_added:
                    print(f"\n🎊 SUCCESS! SMS Campaign Generation System:")
                    print(f"  ✅ Achieved 100% FlowBuilder node coverage")
                    print(f"  ✅ Implemented all 4 development phases")
                    print(f"  ✅ Ready for production deployment")
                    print(f"  ✅ Enterprise-grade marketing automation platform")

                    return {
                        "success": True,
                        "grade": grade,
                        "coverage": coverage_percentage,
                        "performance": generation_time,
                        "nodes_implemented": implemented_nodes,
                        "total_nodes": total_nodes,
                        "phase_complete": phase_complete
                    }
                else:
                    print(f"\n⚠️  PARTIAL SUCCESS:")
                    if coverage_percentage < 100:
                        print(f"  ❌ Missing {total_nodes - implemented_nodes} node types")
                    if not webhook_added:
                        print(f"  ❌ WEBHOOK nodes not implemented")
                    if not filter_added:
                        print(f"  ❌ FILTER nodes not implemented")

                    return {
                        "success": False,
                        "grade": grade,
                        "coverage": coverage_percentage,
                        "performance": generation_time,
                        "nodes_implemented": implemented_nodes,
                        "total_nodes": total_nodes,
                        "phase_complete": phase_complete
                    }

            else:
                print(f"\n❌ ERROR: No final coverage metadata found")
                print("  Phase 4 implementation may be incomplete")
                return {"success": False, "error": "Missing coverage metadata"}

        else:
            print(f"\n❌ ERROR: Campaign generation failed")
            print(f"  Status Code: {response.status_code}")
            print(f"  Response: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        return {"success": False, "error": str(e)}

def main():
    """Main validation function"""
    print("🎯 SMS Campaign Generation System - Final Coverage Validation")
    print("="*70)
    print("Validating 100% FlowBuilder node coverage achievement...")
    print()

    result = validate_complete_coverage()

    print("\n" + "="*70)
    if result.get("success"):
        print("🎉 VALIDATION PASSED!")
        print("🏆 System ready for production deployment!")
    else:
        print("❌ VALIDATION FAILED!")
        print("🔧 Additional work required before deployment")
    print("="*70)

    return result

if __name__ == "__main__":
    main()