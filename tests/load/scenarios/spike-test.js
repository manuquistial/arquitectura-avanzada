/**
 * K6 Spike Test
 * 
 * Tests sudden traffic spike (e.g., viral event, news mention).
 * 
 * Usage:
 *   k6 run scenarios/spike-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '1m', target: 10 },    // Normal load
    { duration: '10s', target: 500 },  // SUDDEN SPIKE! ⚡
    { duration: '3m', target: 500 },   // Sustain spike
    { duration: '10s', target: 10 },   // Drop back
    { duration: '1m', target: 10 },    // Normal load
    { duration: '10s', target: 0 },    // End
  ],
  
  thresholds: {
    'http_req_duration': ['p(95)<2000'],  // During spike, allow higher latency
    'http_req_failed': ['rate<0.1'],      // Allow up to 10% errors during spike
    'errors': ['rate<0.1'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/api/documents`);
  
  const success = check(res, {
    'status 200': (r) => r.status === 200,
    'latency < 5s': (r) => r.timings.duration < 5000,
  });
  
  errorRate.add(!success);
  
  sleep(0.5);
}

export function handleSummary(data) {
  console.log(`\n⚡ Spike Test Results:`);
  console.log(`   Peak VUs: 500`);
  console.log(`   P95 Latency: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  console.log(`   Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%`);
  console.log(`   System handled spike: ${data.metrics.http_req_failed.values.rate < 0.1 ? '✅ YES' : '❌ NO'}`);
  
  return {
    'spike-test-results.json': JSON.stringify(data, null, 2),
  };
}

