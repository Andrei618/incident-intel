"""Hand-authored fixture data for the RAG eval (documents, tickets)."""

from datetime import date

DOCUMENTS = [
    {
        "service": "payment-service",
        "doc_key": "payment-db-pool-runbook",
        "title": "Payment Service DB Connection Pool Troubleshooting",
        "doc_type": "runbook",
        "content": """\
# Payment Service DB Connection Pool Troubleshooting

## Symptoms
- Timeout errors in payment-service logs: "connection pool exhausted"
- PostgreSQL logs showing "FATAL: remaining connection slots are reserved"
- Elevated 503 error rate on /api/v1/checkout and /api/v1/payments endpoints
- pg_stat_activity shows connections near max_connections limit

## Diagnosis

### Step 1: Check current connection count
```bash
psql -h payment-db.internal -U admin -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'payments'"
```

### Step 2: Identify long-running queries holding connections
```bash
psql -h payment-db.internal -U admin -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE datname = 'payments' AND state != 'idle' ORDER BY duration DESC LIMIT 10"
```

### Step 3: Check application pool configuration
```bash
kubectl exec -it deployment/payment-service -- cat /app/config/db.yaml | grep pool
```

Expected: pool_size=20, max_overflow=10, pool_timeout=30

## Resolution
### Immediate: Kill idle connections
```bash
psql -h payment-db.internal -U admin -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'payments' AND state = 'idle' AND query_start < now() - interval '5 minutes'"
```

### Short-term: Restart pods to reset connection pools
```bash
kubectl rollout restart deployment/payment-service -n production
```

### Long-term: Tune pool settings
If recurring, increase pool_size in deployment config and consider PgBouncer for connection pooling at the infrastructure level.

## Escalation
- If connections do not drop after pod restart: page DBA team
- If PostgreSQL itself is unresponsive: see Database Failover Runbook
""",
    },
    {
        "service": "api-gateway",
        "doc_key": "api-gateway-rate-limit-runbook",
        "title": "API Gateway Rate Limit Configuration",
        "doc_type": "runbook",
        "content": """\
# API Gateway Rate Limit Configuration

## Symptoms
- Customers receiving HTTP 429 Too Many Requests errors
- Response headers showing incorrect X-RateLimit-Limit values
- Rate limiter Redis keys showing wrong thresholds per API key
- Customer complaints about requests being throttled below their plan tier

## Diagnosis

### Step 1: Check current rate limit configuration
```bash
kubectl exec -it deployment/api-gateway -n production -- cat /app/config/rate-limits.yaml
```

Verify tier limits match expected values:
- Free: 50 req/s
- Pro: 200 req/s
- Enterprise: 500 req/s

### Step 2: Check rate limit counters in Redis
```bash
redis-cli -h redis.internal -n 2 GET "rate_limit:apikey:<customer-api-key>"
redis-cli -h redis.internal -n 2 TTL "rate_limit:apikey:<customer-api-key>"
```

### Step 3: Verify customer tier mapping
```bash
curl -s http://api-gateway.internal:8080/admin/api-keys/<key> | jq '.tier'
```

### Step 4: Check recent config deployments
```bash
kubectl rollout history deployment/api-gateway -n production
git log --oneline -10 -- config/rate-limits.yaml
```

## Resolution

### Immediate: Update rate limit config with correct tier values
```bash
kubectl edit configmap api-gateway-config -n production
```

###Set correct values per tier, then restart:
```bash
kubectl rollout restart deployment/api-gateway -n production
```

### Clear stale rate limit counters in Redis
```bash
redis-cli -h redis.internal -n 2 KEYS "rate_limit:*" | xargs redis-cli -h redis.internal -n 2 DEL
```

### Verify fix: Test with affected customer's API key
```bash
for i in $(seq 1 10); do curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: <key>" https://api.company.com/v1/health; echo; done
```
All responses should be 200, not 429.

## Prevent recurrence
- Add config validation in CI/CD pipeline to reject rate limit configs below tier minimums
- Add integration test that verifies each tier gets correct rate limit headers
- Set up alerting when enterprise customers hit 429 errors

## Escalation
- If rate limits cannot be updated via config: page api-gateway team lead
- If Redis is unresponsive: see Redis Cluster Troubleshooting Runbook
""",
    },
    {
        "service": "auth-service",
        "doc_key": "auth-service-memory-runbook",
        "title": "Auth Service Memory Troubleshooting",
        "doc_type": "runbook",
        "content": """\
# Auth Service Memory Troubleshooting

## Symptoms
- Kubernetes pods restarting with reason "OOMKilled" and exit code 137
- Container memory usage growing linearly over time without stabilizing
- Increased login failures and 502 errors during pod restarts
- Grafana memory dashboard showing sawtooth pattern (gradual rise, sudden drop)

## Diagnosis

### Step 1: Check pod restart history and OOM events
```bash
kubectl get pods -n production -l app=auth-service -o wide
kubectl describe pod <pod-name> -n production | grep -A 5 "Last State"
```

### Step 2: Monitor real-time memory usage
```bash
kubectl top pods -n production -l app=auth-service
```

Run this every 30 seconds to observe the growth pattern.

### Step 3: Capture heap dump before OOM
```bash
kubectl exec -it <pod-name> -n production -- jmap -dump:format=b,file=/tmp/heap.hprof 1
kubectl cp production/<pod-name>:/tmp/heap.hprof ./heap.hprof
```

### Step 4: Check JVM or runtime memory settings
```bash
kubectl exec -it <pod-name> -n production -- env | grep -i memory
kubectl get deployment auth-service -n production -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

## Resolution

### Immediate: Increase memory limit to buy time
```bash
kubectl set resources deployment/auth-service -n production --limits=memory=1Gi
```

### Short-term: Restart pods on a schedule to prevent OOM
```bash
kubectl rollout restart deployment/auth-service -n production
```

### Long-term: Fix the memory leak
Review session cache eviction policy — ensure expired JWT tokens are removed
Add TTL-based eviction to in-memory cache
Consider moving session cache to Redis instead of in-process memory

## Escalation
- If heap dump shows leak outside application code: page platform engineering team
- If login success rate drops below 50%: escalate to P1
""",
    },
    {
        "service": "monitoring",
        "doc_key": "monitoring-disk-space-runbook",
        "title": "Disk Space Management Guide",
        "doc_type": "runbook",
        "content": """\
# Disk Space Management Guide
## Symptoms
- Alertmanager alert "DiskSpaceCritical" for monitoring nodes
- df -h shows /var/log partition above 90%
- Logrotate not running — stale /var/lib/logrotate/logrotate.status
- Elasticsearch refusing to index new documents with "flood stage disk watermark exceeded"

## Diagnosis

### Step 1: Identify what is consuming disk space
```bash
du -sh /var/log/* | sort -rh | head -20
```

### Step 2: Check logrotate status and errors
```bash
cat /var/lib/logrotate/logrotate.status
logrotate -d /etc/logrotate.conf 2>&1 | grep error
```

The -d flag runs logrotate in debug mode without actually rotating.

### Step 3: Check Elasticsearch index sizes
```bash
curl -s http://localhost:9200/_cat/indices?v&s=store.size:desc | head -20
```

### Step 4: Verify cron is running logrotate
```bash
systemctl status crond
grep logrotate /var/log/cron
```

## Resolution

### Immediate: Free disk space by removing old logs
```bash
find /var/log -name "*.gz" -mtime +7 -delete
journalctl --vacuum-size=500M
```

### Fix logrotate: Run manually and fix configuration
```bash
logrotate -f /etc/logrotate.conf
```
If this fails, check for syntax errors in /etc/logrotate.d/ config files.

### Clean old Elasticsearch indices
```bash
curator_cli --host localhost delete_indices --filter_list '[{"filtertype":"age","source":"creation_date","direction":"older","unit":"days","unit_count":30}]'
```

### Prevent recurrence
- Verify logrotate cron entry exists: cat /etc/cron.daily/logrotate
- Set up Elasticsearch ILM (Index Lifecycle Management) policy for automatic index deletion
- Add disk usage monitoring alert at 80% threshold as early warning

## Escalation
- If disk reaches 98% and cannot free space: page infrastructure team immediately
- If Elasticsearch cluster goes red: see Elasticsearch Cluster Recovery Runbook
""",
    },
    {
        "service": "infra-vpn",
        "doc_key": "vpn-cert-renewal-runbook",
        "title": "VPN Certificate Renewal Runbook",
        "doc_type": "runbook",
        "content": """\
# VPN Certificate Renewal Runbook

## Symptoms
- VPN client connections failing with "TLS handshake failed"
- Users reporting "certificate has expired" or "SSL_ERROR_EXPIRED_CERT_ALERT"
- OpenVPN/WireGuard logs showing TLS negotiation failures
- Spike in helpdesk tickets from remote employees unable to connect

## Diagnosis

### Step 1: Check certificate expiration date
```bash
openssl x509 -in /etc/openvpn/server.crt -noout -dates
```

Look for notAfter — if this date is in the past, the certificate has expired.

### Step 2: Verify certificate chain
```bash
openssl verify -CAfile /etc/openvpn/ca.crt /etc/openvpn/server.crt
```

### Step 3: Check certbot renewal status
```bash
certbot certificates --domain vpn.company.internal
```

## Resolution
### Immediate: Renew certificate manually
```bash
certbot renew --cert-name vpn.company.internal --force-renewal
```

### Restart VPN service to load new certificate
```bash
systemctl restart openvpn@server
```

### Verify new certificate is loaded
```bash
openssl s_client -connect vpn.company.internal:443 2>/dev/null | openssl x509 -noout -dates
```

### Prevent recurrence: Enable auto-renewal
```bash
# Add to crontab
echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl restart openvpn@server'" | crontab -
```

## Escalation
- If certificate cannot be renewed (CA issues): page infrastructure security team
- If VPN service does not restart after renewal: see VPN Gateway Recovery Runbook
""",
    },
]


EVAL_TODAY = date(2026, 6, 1)


TICKETS = [
    {"service": "payment-service", "days_ago": 2, "status": "open", "priority": "p1"},
    {"service": "api-gateway", "days_ago": 4, "status": "open", "priority": "p3"},
    {"service": "auth-service", "days_ago": 6, "status": "in_progress", "priority": "p2"},
    {"service": "payment-service", "days_ago": 12, "status": "open", "priority": "p2"},
    {"service": "monitoring", "days_ago": 18, "status": "resolved", "priority": "p3"},
    {"service": "auth-service", "days_ago": 22, "status": "open", "priority": "p4"},
    {"service": "api-gateway", "days_ago": 28, "status": "resolved", "priority": "p2"},
    {"service": "payment-service", "days_ago": 35, "status": "resolved", "priority": "p1"},
    {"service": "infra-vpn", "days_ago": 40, "status": "closed", "priority": "p2"},
    {"service": "monitoring", "days_ago": 45, "status": "in_progress", "priority": "p3"},
    {"service": "infra-vpn", "days_ago": 55, "status": "closed", "priority": "p3"},
    {"service": "auth-service", "days_ago": 60, "status": "resolved", "priority": "p4"},
]
