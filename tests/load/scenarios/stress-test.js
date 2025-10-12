/**
 * K6 Stress Test
 * 
 * Gradually increases load to find breaking point.
 * 
 * Usage:
 *   k6 run scenarios/stress-test.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100
    { duration: '5m', target: 100 },   // Stay at 100
    { duration: '2m', target: 200 },   // Increase to 200
    { duration: '5m', target: 200 },   // Stay at 200
    { duration: '2m', target: 300 },   // Increase to 300
    { duration: '5m', target: 300 },   // Stay at 300
    { duration: '2m', target: 400 },   // Increase to 400
    { duration: '5m', target: 400 },   // Find breaking point
    { duration: '5m', target: 0 },     // Ramp down
  ],
  
  thresholds: {
    // Expect some failures at high load
    'http_req_duration': ['p(95)<5000'],
    'http_req_failed': ['rate<0.5'],  // Allow up to 50% errors at breaking point
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  const res = http.get(`${BASE_URL}/api/documents`);
  
  check(res, {
    'status < 500': (r) => r.status < 500,  // Not server error
  });
  
  sleep(0.5);  // Aggressive
}

export function handleSummary(data) {
  const maxVUs = Math.max(...data.metrics.vus.values);
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  const errorRate = data.metrics.http_req_failed.values.rate;
  
  console.log(`\n🔥 Stress Test Results:`);
  console.log(`   Max VUs: ${maxVUs}`);
  console.log(`   P95 Latency: ${p95.toFixed(2)}ms`);
  console.log(`   Error Rate: ${(errorRate * 100).toFixed(2)}%`);
  console.log(`   Breaking Point: ${errorRate > 0.1 ? 'REACHED' : 'NOT REACHED'}`);
  
  return {
    'stress-test-results.json': JSON.stringify(data, null, 2),
  };
}

