# Test and load-test results

## Kubernetes API Load Test — 2026-10-25

### Environment
- Deployment: `hoplid-api` on local Docker Desktop Kubernetes
- Database: PostgreSQL
- Access path: Kubernetes Service through local port-forward
- Requests: 200 unique order creation requests
- Client concurrency: 20 worker threads

### Results
| Metric | Observed result |
|---|---:|
| Total duration | 5.86 seconds |
| Throughput | 34.14 requests/second |
| Successful HTTP responses (2xx) | 200 |
| Non-2xx or failed requests | 0 |
| Error rate | 0.00% |
| p50 latency | 517.64 ms |
| p95 latency | 937.02 ms |
| p99 latency | 1046.15 ms |

### Kubernetes observations
- HPA CPU target: 2% / 70%
- Minimum and maximum replicas: 2 and 5
- Replicas observed after the test: 2
- Pod CPU: approximately 2–3 millicores
- Pod memory: approximately 59–60 MiB
- Pod restarts: 0

### Interpretation and limitations
All 200 requests succeeded in this run. The workload did not trigger scale-up because measured CPU utilization remained well below the HPA target. These are local-environment results, not production capacity guarantees. The test does not by itself establish behavior during database failure, sustained overload, or a rolling deployment under traffic.
