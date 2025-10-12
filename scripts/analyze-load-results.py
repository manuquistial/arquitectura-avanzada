#!/usr/bin/env python3
"""
Analyze k6 load test results
Checks if SLOs were met and generates report
"""

import json
import sys
from pathlib import Path


def analyze_k6_results(results_file: str):
    """
    Analyze k6 summary results.
    
    Args:
        results_file: Path to k6 summary JSON file
    """
    with open(results_file) as f:
        data = json.load(f)
    
    metrics = data.get('metrics', {})
    
    print("\n" + "=" * 60)
    print("📊 K6 LOAD TEST RESULTS ANALYSIS")
    print("=" * 60)
    
    # HTTP Request Duration (SLO: P95 < 500ms)
    if 'http_req_duration' in metrics:
        p95 = metrics['http_req_duration']['values']['p(95)']
        p99 = metrics['http_req_duration']['values']['p(99)']
        avg = metrics['http_req_duration']['values']['avg']
        
        print(f"\n⏱️  HTTP Request Duration:")
        print(f"   Average: {avg:.2f}ms")
        print(f"   P95: {p95:.2f}ms {'✅' if p95 < 500 else '❌'} (SLO: <500ms)")
        print(f"   P99: {p99:.2f}ms {'✅' if p99 < 2000 else '❌'} (SLO: <2000ms)")
    
    # Error Rate (SLO: < 0.1%)
    if 'http_req_failed' in metrics:
        error_rate = metrics['http_req_failed']['values']['rate'] * 100
        
        print(f"\n❌ Error Rate:")
        print(f"   {error_rate:.3f}% {'✅' if error_rate < 0.1 else '❌'} (SLO: <0.1%)")
    
    # Request Rate
    if 'http_reqs' in metrics:
        total_reqs = metrics['http_reqs']['values']['count']
        rate = metrics['http_reqs']['values']['rate']
        
        print(f"\n📈 Throughput:")
        print(f"   Total requests: {total_reqs}")
        print(f"   Requests/sec: {rate:.2f}")
    
    # Virtual Users
    if 'vus' in metrics:
        max_vus = int(metrics['vus']['values']['max'])
        
        print(f"\n👥 Virtual Users:")
        print(f"   Max VUs: {max_vus}")
    
    # Custom Metrics
    if 'document_upload_duration' in metrics:
        p95 = metrics['document_upload_duration']['values']['p(95)']
        print(f"\n📤 Document Upload P95: {p95:.2f}ms {'✅' if p95 < 3000 else '❌'} (SLO: <3000ms)")
    
    if 'search_duration' in metrics:
        p95 = metrics['search_duration']['values']['p(95)']
        print(f"🔍 Search P95: {p95:.2f}ms {'✅' if p95 < 500 else '❌'} (SLO: <500ms)")
    
    if 'rate_limit_hits' in metrics:
        hits = int(metrics['rate_limit_hits']['values']['count'])
        print(f"🚦 Rate Limit Hits: {hits} {'✅' if hits < 100 else '⚠️'}")
    
    # Check if all SLOs met
    print("\n" + "=" * 60)
    
    slos_met = True
    
    if 'http_req_duration' in metrics:
        if metrics['http_req_duration']['values']['p(95)'] >= 500:
            slos_met = False
            print("❌ SLO VIOLATION: P95 latency >= 500ms")
        
        if metrics['http_req_duration']['values']['p(99)'] >= 2000:
            slos_met = False
            print("❌ SLO VIOLATION: P99 latency >= 2s")
    
    if 'http_req_failed' in metrics:
        if metrics['http_req_failed']['values']['rate'] >= 0.001:
            slos_met = False
            print("❌ SLO VIOLATION: Error rate >= 0.1%")
    
    if slos_met:
        print("✅ ALL SLOs MET! System performance is excellent.")
    else:
        print("⚠️  SOME SLOs NOT MET. Review results and optimize.")
        sys.exit(1)
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze-load-results.py <k6-summary.json>")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    if not Path(results_file).exists():
        print(f"Error: File not found: {results_file}")
        sys.exit(1)
    
    analyze_k6_results(results_file)

