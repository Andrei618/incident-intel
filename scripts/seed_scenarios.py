"""Seed Data: 5 scenarios matching ticket + runbook pairs for testing of search.

For each of 5 scenarios, creates:
- Service (via ORM — AsyncSession + Service model)
- Ticket (via API — POST /api/v1/tickets)
- Runbook document (via API — POST /api/v1/documents, doc_type="runbook")
Provides semantically coherent data for BM25, vector, hybrid search.
"""

import asyncio
from typing import Any
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import Session
from incident_intel.main import app
from incident_intel.models.service import Service

# SCENARIOS - but it looks too complex
SCENARIOS: list[dict[str, dict[str, Any]]] = [
    {  # Scenario 1: payment-service — DB connection pool exhaustion
        "service": {
            "name": "payment-service",
            "description": "Processes credit card and digital wallet payments via Stripe and PayPal integrations",
        },
        "ticket": {
            "title": "payment-service: database connection pool exhaustion causing timeouts",
            "description": (
                "payment-service is experiencing intermittent 503 errors. "
                "Application logs show 'FATAL: remaining connection slots are reserved' "
                "and 'connection pool exhausted, timeout after 30s waiting for available connection'. "
                "PostgreSQL max_connections is set to 100 but pg_stat_activity shows 98 active connections. "
                "Checkout flow is failing for approximately 40% of users. "
                "Started around 14:30 UTC after a traffic spike from a marketing campaign."
            ),
            "priority": "p1",
            "assignee": "John Doe",
            "reporter": "Amy Chen",
        },
        "document": {
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
    },
    {  # Scenario 2: infra-vpn — VPN certificate expired
        "service": {
            "name": "infra-vpn",
            "description": "Corporate VPN gateway for remote employee access to internal services",
        },
        "ticket": {
            "title": "infra-vpn: TLS certificate expired, all remote connections failing",
            "description": (
                "All remote employees unable to connect to corporate VPN since 08:00 UTC. "
                "VPN client logs show 'TLS handshake failed: certificate has expired' "
                "and 'SSL_ERROR_EXPIRED_CERT_ALERT'. "
                "Certificate CN=vpn.company.internal expired at 2024-02-18T23:59:59Z. "
                "Approximately 200 remote workers are locked out of internal systems. "
                "Auto-renewal via certbot was not configured for VPN gateway certificate."
            ),
            "priority": "p1",
            "assignee": "Sarah Kim",
            "reporter": "Mike Torres",
        },
        "document": {
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
    },
    {  # Scenario 3: auth-service — Memory leak causing OOM kills
        "service": {
            "name": "auth-service",
            "description": "Handles user authentication, JWT token issuance, and session management",
        },
        "ticket": {
            "title": "auth-service: pods restarting due to OOMKilled, memory leak suspected",
            "description": (
                "auth-service pods are being OOMKilled every 2-3 hours. "
                "Kubernetes events show 'Last State: Terminated, Reason: OOMKilled, Exit Code: 137'. "
                "Container memory usage grows linearly from 256Mi to the 512Mi limit before being killed. "
                "Heap dump analysis suggests JWT session cache is not evicting expired tokens. "
                "Login success rate has dropped to 70% due to pods cycling. "
                "Issue started after deploy v2.4.1 which introduced in-memory session caching."
            ),
            "priority": "p2",
            "assignee": "Lisa Park",
            "reporter": "David Nguyen",
        },
        "document": {
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
    },
    {  # Scenario 4: monitoring — Disk space full, log rotation failure
        "service": {
            "name": "monitoring",
            "description": "Centralized logging and metrics collection via Prometheus, Grafana, and ELK stack",
        },
        "ticket": {
            "title": "monitoring: disk usage at 94%, log rotation not running",
            "description": (
                "Monitoring server /var/log partition is at 94% capacity and growing. "
                "Alertmanager fired 'DiskSpaceCritical' alert for monitoring-node-01. "
                "Logrotate cron job has not executed since last Tuesday — "
                "/var/lib/logrotate/logrotate.status shows last run 5 days ago. "
                "Elasticsearch logs are consuming 12GB/day and oldest indices are not being cleaned up. "
                "If disk reaches 100%, Prometheus and Elasticsearch will stop ingesting data "
                "and we will lose observability across all services."
            ),
            "priority": "p2",
            "assignee": "Carlos Ruiz",
            "reporter": "Priya Sharma",
        },
        "document": {
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
    },
    {  # Scenario 5: api-gateway — Rate limiting too aggressive
        "service": {
            "name": "api-gateway",
            "description": "Central API gateway handling request routing, authentication, and rate limiting for all public APIs",
        },
        "ticket": {
            "title": "api-gateway: legitimate requests being rejected with 429 Too Many Requests",
            "description": (
                "Multiple enterprise customers reporting HTTP 429 responses from api-gateway. "
                "Rate limiter is rejecting requests at 50 req/s per API key but enterprise tier "
                "should allow 500 req/s. "
                "Response headers show 'X-RateLimit-Limit: 50' and 'Retry-After: 60' for all tiers. "
                "Root cause appears to be config deployment from yesterday that reset all rate limit "
                "tiers to the default free-tier value. "
                "Affected customers: Acme Corp, GlobalTech, DataFlow Inc — all on enterprise plans."
            ),
            "priority": "p2",
            "assignee": "Rachel Adams",
            "reporter": "Tom Bradley",
        },
        "document": {
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
    },
]


async def ensure_service(session: AsyncSession, service_data: dict[str, Any]) -> UUID:
    """Query Service by name, create if not found.

    ORM query-then-insert.
    """
    # check tha service_id exist
    stmt = select(Service.id).where(Service.name == service_data["name"])
    service_id = await session.scalar(stmt)

    if service_id is None:
        new_service = Service(**service_data)
        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)
        service_id = new_service.id

    return service_id


async def seed_scenario(
    client: AsyncClient,
    service_id: UUID,
    ticket_data: dict[str, str],  # without service_id
    document_data: dict[str, str],  # without service_id
) -> None:
    """Seed data for tickets and documents via existing API POST endpoints."""
    # Inject service_id
    payload_ticket = {**ticket_data, "service_id": str(service_id)}
    payload_document = {**document_data, "service_id": str(service_id)}

    # do we need try-except here or just check response.status_code? or other way?
    response_ticket = await client.post("/api/v1/tickets", json=payload_ticket)
    response_ticket.raise_for_status()
    print(f"Created ticket: {response_ticket.json()['title']}")

    response_document = await client.post("/api/v1/documents", json=payload_document)
    response_document.raise_for_status()
    print(f"Created document: {response_document.json()['title']}")


async def main() -> None:
    """."""
    service_ids = []
    async with Session() as session:
        for scenario in SCENARIOS:
            service_id = await ensure_service(
                session=session,
                service_data=scenario["service"],
            )
            service_ids.append(service_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for scenario, service_id in zip(SCENARIOS, service_ids, strict=True):
            await seed_scenario(
                client=client,
                service_id=service_id,
                ticket_data=scenario["ticket"],
                document_data=scenario["document"],
            )


if __name__ == "__main__":
    asyncio.run(main())
