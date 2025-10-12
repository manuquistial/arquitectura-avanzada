/**
 * K6 Baseline Performance Test
 * 
 * Tests normal operations to establish baseline metrics.
 * 
 * Usage:
 *   k6 run scenarios/api-baseline.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');

export const options = {
  vus: 10,
  duration: '5m',
  
  thresholds: {
    'http_req_duration': ['p(95)<500'],  // 95% < 500ms (SLO)
    'http_req_failed': ['rate<0.001'],   // < 0.1% errors (SLO)
    'errors': ['rate<0.001'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // Health check
  let res = http.get(`${BASE_URL}/health`);
  
  check(res, {
    'health check OK': (r) => r.status === 200,
    'health check fast': (r) => r.timings.duration < 100,
  });
  
  errorRate.add(res.status !== 200);
  apiLatency.add(res.timings.duration);
  
  // Metrics endpoint
  res = http.get(`${BASE_URL}/metrics`);
  
  check(res, {
    'metrics OK': (r) => r.status === 200,
  });
  
  errorRate.add(res.status !== 200);
  
  sleep(1);
}

