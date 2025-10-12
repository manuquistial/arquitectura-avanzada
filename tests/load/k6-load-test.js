/**
 * K6 Load Testing Script for Carpeta Ciudadana
 * 
 * Tests:
 * - POST /documents (upload)
 * - GET /search (search documents)
 * - POST /api/transferCitizen (P2P transfer)
 * 
 * Usage:
 *   k6 run k6-load-test.js
 *   k6 run --vus 10 --duration 30s k6-load-test.js
 *   k6 run --vus 50 --duration 2m k6-load-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const documentUploadDuration = new Trend('document_upload_duration');
const searchDuration = new Trend('search_duration');
const transferDuration = new Trend('transfer_duration');
const rateLimitHits = new Counter('rate_limit_hits');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';

// Test scenarios
export const options = {
  scenarios: {
    // Scenario 1: Normal Load (baseline)
    normal_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },   // Ramp up
        { duration: '3m', target: 20 },   // Sustain
        { duration: '1m', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '30s',
    },
    
    // Scenario 2: Peak Load (lunch hour)
    peak_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      startTime: '5m',
      stages: [
        { duration: '2m', target: 100 },  // Ramp up to peak
        { duration: '5m', target: 100 },  // Sustain peak
        { duration: '2m', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '30s',
    },
    
    // Scenario 3: Stress Test (find breaking point)
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      startTime: '14m',
      stages: [
        { duration: '2m', target: 100 },
        { duration: '2m', target: 200 },
        { duration: '2m', target: 300 },
        { duration: '2m', target: 400 },
        { duration: '5m', target: 0 },
      ],
      gracefulRampDown: '30s',
    },
    
    // Scenario 4: Spike Test (sudden traffic)
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      startTime: '27m',
      stages: [
        { duration: '10s', target: 200 },  // Sudden spike
        { duration: '1m', target: 200 },   // Hold spike
        { duration: '10s', target: 0 },    // Drop
      ],
    },
  },
  
  thresholds: {
    // SLO-based thresholds (from SLOS_SLIS.md)
    'http_req_duration': ['p(95)<500', 'p(99)<2000'],  // P95 < 500ms, P99 < 2s
    'http_req_failed': ['rate<0.001'],                 // Error rate < 0.1%
    'errors': ['rate<0.001'],
    
    // Specific operation thresholds
    'document_upload_duration': ['p(95)<3000'],        // Upload < 3s
    'search_duration': ['p(95)<500'],                  // Search < 500ms
    'transfer_duration': ['p(95)<2000'],               // Transfer < 2s
    
    // Rate limiting
    'rate_limit_hits': ['count<100'],                  // < 100 rate limit hits
  },
};

// Generate random test data
function generateCitizenId() {
  return Math.floor(1000000000 + Math.random() * 9000000000).toString();
}

function generateDocumentData() {
  return {
    title: `Test Document ${Date.now()}`,
    description: 'Load test document',
    citizenId: generateCitizenId(),
    sha256Hash: `${Date.now()}_hash`,
    sizeBytes: Math.floor(1000 + Math.random() * 10000),
    contentType: 'application/pdf',
    filename: `test_${Date.now()}.pdf`
  };
}

// Setup function
export function setup() {
  console.log('Starting load test...');
  console.log(`Base URL: ${BASE_URL}`);
  return { startTime: Date.now() };
}

// Main test function
export default function(data) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
  };
  
  // Weight different operations
  const operation = Math.random();
  
  if (operation < 0.5) {
    // 50% - Document upload
    testDocumentUpload(headers);
  } else if (operation < 0.8) {
    // 30% - Search
    testSearch(headers);
  } else {
    // 20% - Transfer
    testTransfer(headers);
  }
  
  sleep(Math.random() * 2 + 1); // Random sleep between 1-3 seconds
}

function testDocumentUpload(headers) {
  group('Document Upload', () => {
    const docData = generateDocumentData();
    
    // Step 1: Request upload URL
    const uploadUrlResponse = http.post(
      `${BASE_URL}/api/documents/upload-url`,
      JSON.stringify({
        filename: docData.filename,
        contentType: docData.contentType,
        citizenId: docData.citizenId
      }),
      { headers }
    );
    
    const uploadUrlSuccess = check(uploadUrlResponse, {
      'upload URL requested': (r) => r.status === 200,
      'has presigned URL': (r) => r.json('presignedUrl') !== undefined,
    });
    
    errorRate.add(!uploadUrlSuccess);
    
    if (!uploadUrlSuccess) {
      if (uploadUrlResponse.status === 429) {
        rateLimitHits.add(1);
      }
      return;
    }
    
    // Step 2: Upload to presigned URL (mock)
    // In real scenario, this would upload to Azure Blob/S3
    sleep(0.5); // Simulate upload time
    
    // Step 3: Confirm upload
    const confirmResponse = http.post(
      `${BASE_URL}/api/documents/confirm-upload`,
      JSON.stringify({
        documentId: uploadUrlResponse.json('documentId'),
        sha256Hash: docData.sha256Hash,
        sizeBytes: docData.sizeBytes
      }),
      { headers }
    );
    
    const confirmSuccess = check(confirmResponse, {
      'upload confirmed': (r) => r.status === 200,
    });
    
    errorRate.add(!confirmSuccess);
    documentUploadDuration.add(confirmResponse.timings.duration);
    
    if (confirmResponse.status === 429) {
      rateLimitHits.add(1);
    }
  });
}

function testSearch(headers) {
  group('Document Search', () => {
    const queries = [
      'certificado',
      'documento',
      'título',
      'identificación',
      'test'
    ];
    
    const query = queries[Math.floor(Math.random() * queries.length)];
    
    const response = http.get(
      `${BASE_URL}/api/metadata/search?q=${query}&limit=20`,
      { headers }
    );
    
    const success = check(response, {
      'search successful': (r) => r.status === 200,
      'has results': (r) => r.json('documents') !== undefined,
      'response time OK': (r) => r.timings.duration < 2000,
    });
    
    errorRate.add(!success);
    searchDuration.add(response.timings.duration);
    
    if (response.status === 429) {
      rateLimitHits.add(1);
    }
  });
}

function testTransfer(headers) {
  group('P2P Transfer', () => {
    const transferData = {
      citizenId: generateCitizenId(),
      destinationOperatorId: 'operator-test',
      token: `transfer_${Date.now()}`
    };
    
    // Step 1: Initiate transfer
    const response = http.post(
      `${BASE_URL}/api/transferCitizen`,
      JSON.stringify(transferData),
      { 
        headers: {
          ...headers,
          'Idempotency-Key': transferData.token
        }
      }
    );
    
    const success = check(response, {
      'transfer initiated': (r) => r.status === 201 || r.status === 202,
      'has transfer ID': (r) => r.json('transferId') !== undefined || r.status === 202,
    });
    
    errorRate.add(!success);
    transferDuration.add(response.timings.duration);
    
    if (response.status === 429) {
      rateLimitHits.add(1);
    }
  });
}

// Teardown function
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`\nLoad test completed in ${duration}s`);
}

// Handle summary
export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'load-test-results.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  let summary = '\n';
  summary += `${indent}Scenarios:\n`;
  summary += `${indent}  Document Upload: ${data.metrics.document_upload_duration.values.count} requests\n`;
  summary += `${indent}  Search: ${data.metrics.search_duration.values.count} requests\n`;
  summary += `${indent}  Transfer: ${data.metrics.transfer_duration.values.count} requests\n`;
  summary += `\n${indent}Performance:\n`;
  summary += `${indent}  HTTP req duration (p95): ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms\n`;
  summary += `${indent}  HTTP req duration (p99): ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms\n`;
  summary += `${indent}  Error rate: ${(data.metrics.errors.values.rate * 100).toFixed(2)}%\n`;
  summary += `${indent}  Rate limit hits: ${data.metrics.rate_limit_hits.values.count}\n`;
  
  return summary;
}

