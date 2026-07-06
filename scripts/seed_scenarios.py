"""Seed Data: 5 scenarios matching ticket + runbook pairs for testing of search.

For each of 5 scenarios, creates:
- Service (via ORM — AsyncSession + Service model)
- Ticket (via API — POST /api/v1/tickets)
- Runbook document (via API — POST /api/v1/documents, doc_type varies (runbook/guide/policy/faq))
Provides semantically coherent data for keyword, vector, hybrid search.
"""

import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from incident_intel.core.database import Session
from incident_intel.main import app
from incident_intel.models.document import Document
from incident_intel.models.service import Service
from incident_intel.models.ticket import Ticket, TicketPriority, TicketStatus

S = TicketStatus
P = TicketPriority
SLA_HOURS = {P.P1: 1, P.P2: 4, P.P3: 24, P.P4: 72}
STATUS_RANK = {S.OPEN: 0, S.IN_PROGRESS: 1, S.RESOLVED: 2, S.CLOSED: 3}

# (days_ago, hour, service, status, priority, title)
SPREAD_TICKETS = [
    # 0-3 days
    (
        0,
        9,
        "payment-service",
        S.OPEN,
        P.P1,
        "payment-service: checkout p95 latency above 2s after deploy",
    ),
    (1, 14, "api-gateway", S.OPEN, P.P3, "api-gateway: 5xx spike on /v1/search route"),
    (
        2,
        11,
        "auth-service",
        S.IN_PROGRESS,
        P.P2,
        "auth-service: login success rate dipped below 95%",
    ),
    # 4-7 days
    (4, 10, "monitoring", S.OPEN, P.P3, "monitoring: Prometheus scrape gaps on node exporters"),
    (5, 16, "infra-vpn", S.OPEN, P.P4, "infra-vpn: intermittent disconnects for EU remote users"),
    (
        6,
        9,
        "payment-service",
        S.OPEN,
        P.P2,
        "payment-service: webhook retries exhausted for Stripe callbacks",
    ),
    (5, 11, "api-gateway", S.IN_PROGRESS, P.P2, "api-gateway: upstream timeouts to auth-service"),
    (
        7,
        15,
        "auth-service",
        S.IN_PROGRESS,
        P.P3,
        "auth-service: password reset emails delayed 10+ minutes",
    ),
    # 8-30 days
    (
        9,
        10,
        "payment-service",
        S.OPEN,
        P.P3,
        "payment-service: duplicate charge reports from reconciliation",
    ),
    (12, 14, "api-gateway", S.OPEN, P.P2, "api-gateway: rate limit config drift between regions"),
    (18, 9, "monitoring", S.OPEN, P.P4, "monitoring: Grafana dashboards slow to load"),
    (25, 13, "infra-vpn", S.OPEN, P.P3, "infra-vpn: MTU mismatch causing slow file transfers"),
    (
        10,
        11,
        "auth-service",
        S.IN_PROGRESS,
        P.P2,
        "auth-service: OAuth refresh token rotation failures",
    ),
    (
        15,
        16,
        "payment-service",
        S.IN_PROGRESS,
        P.P3,
        "payment-service: payment intents stuck in requires_capture",
    ),
    (21, 10, "api-gateway", S.IN_PROGRESS, P.P2, "api-gateway: route cache stale after deploy"),
    (
        28,
        14,
        "monitoring",
        S.IN_PROGRESS,
        P.P4,
        "monitoring: noisy disk alerts causing alert fatigue",
    ),
    (11, 9, "auth-service", S.RESOLVED, P.P1, "auth-service: MFA push notifications not delivered"),
    (
        16,
        15,
        "payment-service",
        S.RESOLVED,
        P.P2,
        "payment-service: refund queue backlog above threshold",
    ),
    (
        22,
        11,
        "infra-vpn",
        S.RESOLVED,
        P.P3,
        "infra-vpn: split DNS resolution failures on macOS clients",
    ),
    (
        27,
        10,
        "api-gateway",
        S.RESOLVED,
        P.P3,
        "api-gateway: websocket upgrade failures for mobile clients",
    ),
    (14, 13, "monitoring", S.CLOSED, P.P2, "monitoring: ELK indexing lag past 15 minutes"),
    (
        29,
        9,
        "payment-service",
        S.CLOSED,
        P.P4,
        "payment-service: settlement report generation timeout",
    ),
    # 31-60 days
    (35, 10, "auth-service", S.OPEN, P.P4, "auth-service: signup captcha false positives"),
    (38, 14, "api-gateway", S.IN_PROGRESS, P.P3, "api-gateway: CORS misconfig for admin console"),
    (52, 9, "monitoring", S.IN_PROGRESS, P.P3, "monitoring: blackbox probes flapping on ap-south"),
    (
        32,
        11,
        "payment-service",
        S.RESOLVED,
        P.P1,
        "payment-service: 3DS challenge failures for EU cards",
    ),
    (36, 15, "infra-vpn", S.RESOLVED, P.P2, "infra-vpn: gateway CPU saturation during peak hours"),
    (
        41,
        10,
        "api-gateway",
        S.RESOLVED,
        P.P2,
        "api-gateway: TLS handshake errors from legacy clients",
    ),
    (
        45,
        13,
        "auth-service",
        S.RESOLVED,
        P.P3,
        "auth-service: SAML assertion clock skew for partner IdP",
    ),
    (
        50,
        9,
        "payment-service",
        S.RESOLVED,
        P.P3,
        "payment-service: card vault sync lag behind primary",
    ),
    (
        57,
        16,
        "monitoring",
        S.RESOLVED,
        P.P4,
        "monitoring: retention policy misapplied to debug logs",
    ),
    (33, 12, "api-gateway", S.CLOSED, P.P1, "api-gateway: global 429s from misapplied rate tier"),
    (43, 10, "infra-vpn", S.CLOSED, P.P2, "infra-vpn: client update rollout blocked on macOS 15"),
    (
        48,
        14,
        "auth-service",
        S.CLOSED,
        P.P3,
        "auth-service: user lockout threshold triggering early",
    ),
    (
        55,
        11,
        "payment-service",
        S.CLOSED,
        P.P2,
        "payment-service: idempotency key collisions on retries",
    ),
    # 61-90 days
    (
        63,
        10,
        "monitoring",
        S.IN_PROGRESS,
        P.P4,
        "monitoring: node exporter version drift across fleet",
    ),
    (
        65,
        9,
        "payment-service",
        S.RESOLVED,
        P.P3,
        "payment-service: chargeback webhook signature mismatch",
    ),
    (70, 14, "api-gateway", S.RESOLVED, P.P3, "api-gateway: canary weights not applied on rollout"),
    (
        76,
        11,
        "auth-service",
        S.RESOLVED,
        P.P2,
        "auth-service: session cache evictions above baseline",
    ),
    (
        82,
        15,
        "infra-vpn",
        S.RESOLVED,
        P.P3,
        "infra-vpn: cert chain warning on newly imaged laptops",
    ),
    (
        67,
        10,
        "payment-service",
        S.CLOSED,
        P.P1,
        "payment-service: PSP outage failover to secondary",
    ),
    (72, 13, "monitoring", S.CLOSED, P.P3, "monitoring: alertmanager silences expired unnoticed"),
    (78, 9, "api-gateway", S.CLOSED, P.P2, "api-gateway: gzip disabled on large response payloads"),
    (85, 14, "auth-service", S.CLOSED, P.P1, "auth-service: JWT signing key rotation incident"),
    (
        88,
        10,
        "payment-service",
        S.CLOSED,
        P.P4,
        "payment-service: sandbox credentials rotated, docs stale",
    ),
]

SCENARIOS: list[dict[str, Any]] = [
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
            "status": S.OPEN,
            "priority": P.P1,
            "assignee": "John Doe",
            "reporter": "Amy Chen",
            "days_ago": 2,
            "hour": 1,
        },
        "documents": [
            {
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
                "title": "Database Connection Pool Sizing Guide",
                "doc_type": "guide",
                "content": """\
# Database Connection Pool Sizing Guide

## Why connection pools matter

Each PostgreSQL connection consumes ~10 MB of memory on the server and holds a backend process. Opening connections per-request is expensive (TCP handshake + auth + session setup) and quickly exhausts `max_connections`. A pool reuses connections across requests.

## Sizing formula

Starting heuristic:

pool_size = (number_of_app_pods x connections_per_pod) ≤ db.max_connections x 0.8



Reserve 20% headroom for replication, monitoring, and ad-hoc DBA sessions.

## Recommended starting values per service tier

| Service tier | pool_size | max_overflow | pool_timeout |
|---|---|---|---|
| Internal (low traffic) | 5 | 5 | 10s |
| Customer-facing (med) | 10 | 5 | 30s |
| High-throughput (payment, auth) | 20 | 10 | 30s |

## When to tune up

- Slow query log shows queries blocked on "waiting for connection"
- p99 latency includes 5-30s gaps that match pool_timeout
- pg_stat_activity shows < 80% of max_connections used during traffic spikes

## When to tune down

- DB CPU is saturated even at low request volume
- Connections sitting idle for > 5 minutes
- Memory pressure on the DB host

## Beyond a single pool: PgBouncer

If you need > 200 concurrent app pods or your DB is shared across services, put PgBouncer in front of PostgreSQL. PgBouncer in transaction-pooling mode lets thousands of app-side connections share a small backend pool.

## Anti-patterns

- Opening per-request connections (no pool at all)
- pool_size > db.max_connections (will fail under load)
- Identical pool_size across dev/staging/prod
""",
            },
            {
                "title": "Payment Service Database FAQ",
                "doc_type": "faq",
                "content": """\
# Payment Service Database FAQ

## Why does payment-service have its own database?

Payment data has stricter compliance requirements (PCI-DSS) than other services. Isolating it limits the audit scope to one DB and reduces blast radius if another service is compromised.

## What's the difference between pool_size and max_overflow?

`pool_size` is the steady-state number of connections held open. `max_overflow` is how many additional connections can be opened temporarily under burst load. Total possible = pool_size + max_overflow.

## How do I know if my queries are causing pool exhaustion?

Check `pg_stat_activity` for queries with state != 'idle' that have been running longer than your pool_timeout. Those are holding connections without releasing them. Common culprits: missing index, unbounded LIMIT, transaction left open by buggy code.

## Can I increase max_connections instead of fixing pool exhaustion?

Short-term yes, long-term no. Each extra connection costs ~10 MB and a backend process. Fix the underlying query patterns instead.

## What happens during a pod restart?

The pool drains gracefully if shutdown is clean (SIGTERM with adequate terminationGracePeriodSeconds). If the pod is OOMKilled, connections are reset abruptly — PostgreSQL will clean them up after tcp_keepalive expires (default 2h; we override to 60s).

## How do I test a query without affecting prod connections?

Use the read replica at `payment-db-read.internal`. It's eventually consistent (~50ms lag) but has its own pool, so heavy analytical queries won't block transactional traffic.

## Who owns the database?

Payment Service team owns the schema. DBA team owns the host, replication, and backups. Cross-service queries are not allowed — go through the payment-service API.
""",
            },
        ],
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
            "status": S.CLOSED,
            "priority": P.P1,
            "assignee": "Sarah Kim",
            "reporter": "Mike Torres",
            "days_ago": 70,
            "hour": 2,
        },
        "documents": [
            {
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
            {
                "title": "Certificate Renewal Policy",
                "doc_type": "policy",
                "content": """\
# Certificate Renewal Policy

## Scope

This policy applies to all TLS certificates issued for internal services, public-facing endpoints, and infrastructure components (VPN gateways, load balancers, mTLS service mesh).

## Ownership

- **Service-level certificates** (api.company.com, payment.company.com): owned by the service team
- **Infrastructure certificates** (vpn.company.internal, mesh CA): owned by the platform team
- **CA root certificate**: owned by infrastructure security team, rotation every 5 years

## Renewal cadence

- Certificates must be valid for at least 30 days at all times
- Auto-renewal is **required** for certificates issued via certbot/Let's Encrypt
- Manual-renewal certificates (e.g. enterprise CA) must be renewed at least 14 days before expiry

## Auto-renewal requirements

Every service deploying a TLS certificate must:

1. Configure certbot or equivalent ACME client with `--post-hook` to reload the service after renewal
2. Register the certificate with the cert-monitor service (cert-monitor.internal)
3. Verify the renewal cron executes — fire-once verification within 30 days of deploy

## Expiry alerts

cert-monitor fires alerts at:

- **60 days before expiry**: ticket created, assignee = certificate owner
- **30 days before expiry**: P3 incident
- **7 days before expiry**: P1 incident, on-call paged

## Audit

Quarterly audit by infrastructure security team. Findings:

- All certificates discoverable via DNS or service mesh must be registered in cert-monitor
- Any certificate not auto-renewing must have a documented runbook and quarterly manual review
- Certificates that have expired in production result in a post-incident review regardless of impact

## Exceptions

Exceptions require approval from infrastructure security team and a documented compensating control.
""",
            },
            {
                "title": "VPN Access FAQ",
                "doc_type": "faq",
                "content": """\
# VPN Access FAQ

## I get "TLS handshake failed" or "certificate has expired" — what do I do?

Wait 5 minutes and try again. If you're seeing this within minutes of the VPN engineer announcing a fix in #incidents, the certificate has been renewed but your client may have cached the old one. Restart your VPN client to clear the cache.

## My VPN client says "certificate not trusted"

This usually means your laptop is missing the corporate CA certificate. Re-run the corporate-laptop-setup script, or download the CA cert from cert-distribution.internal/ca.crt and install via Keychain (macOS) or certmgr.msc (Windows).

## How do I know which VPN to use?

- **Standard remote access**: vpn.company.internal (OpenVPN client config in ~/Documents/vpn/)
- **Privileged access** (production servers, DBs): pam-vpn.internal — requires hardware token
- **Site-to-site partners**: handled at the gateway level, end users do nothing

## Can I connect from a personal device?

No. Only managed corporate devices may connect to corporate VPN. This is enforced via client certificate; personal devices won't have the corporate cert.

## Why does the VPN sometimes drop after exactly 8 hours?

Session lifetime is capped at 8 hours by policy. Reconnect; you'll get a fresh session.

## Who do I contact when the VPN is down?

Check #infra-alerts first — most VPN outages are already known. If not, open a ticket against `infra-vpn` service with priority based on impact. The on-call for infra is paged automatically for P1.

## Can I use split tunneling?

No, by policy all corporate traffic is routed through VPN for DLP inspection. Non-corporate traffic bypasses the VPN locally.
""",
            },
        ],
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
            "status": S.IN_PROGRESS,
            "priority": P.P2,
            "assignee": "Lisa Park",
            "reporter": "David Nguyen",
            "days_ago": 21,
            "hour": 3,
        },
        "documents": [
            {
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
                "title": "Memory Profiling Guide for JVM Services",
                "doc_type": "guide",
                "content": """\
# Memory Profiling Guide for JVM Services

## When to profile

- Pod restarts with reason `OOMKilled` and exit code 137
- Memory growth pattern is linear or sawtooth in Grafana
- Heap usage stays high after garbage collection completes
- Application becomes unresponsive but does not crash

## Tools

| Tool | What it shows | When to use |
|---|---|---|
| `kubectl top pod` | Container memory usage | First-look, real-time |
| `jstat -gc <pid>` | GC pause time, heap regions | Confirms GC is healthy |
| `jmap -dump:format=b` | Full heap snapshot | Captures objects for analysis |
| Eclipse MAT / VisualVM | Heap dump analysis | Find largest retainers |
| async-profiler | Allocation flamegraph | Find allocation hotspots |

## Workflow

### 1. Confirm it's a memory issue, not GC

```bash
kubectl exec -it <pod> -- jstat -gc 1 1000
If FGCT (full GC time) is climbing fast, GC is the bottleneck. If OU (old gen used) plateaus at the heap limit, there's a leak.

2. Capture a heap dump before OOM
Set -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap.hprof in JVM args.

Or trigger manually:


kubectl exec -it <pod> -- jmap -dump:format=b,file=/tmp/heap.hprof 1
kubectl cp <pod>:/tmp/heap.hprof ./heap.hprof
3. Analyze with MAT
Open the .hprof in Eclipse MAT. Run Leak Suspects Report — it identifies dominator trees and points to the class/objects holding most memory.

Common findings:

Unbounded cache: a Map<String, T> that grows forever
Thread-local leak: short-lived threads leaving large objects in ThreadLocal
Listener leak: callbacks registered but never deregistered
String interning: heavy use of String.intern() exhausts perm gen
Resolution patterns
Use Caffeine or Guava cache with size limit + TTL
Audit ThreadLocal usage; call .remove() in finally
Move per-session state out of process memory (use Redis) """,
            },
            {
                "title": "Service Resource Limits Policy",
                "doc_type": "policy",
                "content": """\
Service Resource Limits Policy
Purpose
All services deployed to Kubernetes must declare CPU and memory resource limits. This protects the cluster from runaway containers, enables fair scheduling, and produces predictable autoscaling behavior.

Mandatory fields
Every Deployment / StatefulSet must declare in its container spec:

resources.requests.cpu — guaranteed CPU allocation
resources.requests.memory — guaranteed memory allocation
resources.limits.cpu — hard ceiling, throttled if exceeded
resources.limits.memory — hard ceiling, OOMKilled if exceeded
Deployments without all four fields will fail admission via OPA Gatekeeper.

Sizing requirements
requests should reflect steady-state usage (median load)
limits should be ≥ 2x requests to absorb traffic spikes
Memory limit should not exceed the JVM heap (-Xmx) + 256Mi overhead
Service tiers
Tier	CPU req	Memory req	Memory limit
Internal tooling	100m	256Mi	512Mi
Customer-facing standard	500m	512Mi	1Gi
Critical-path (auth, payment)	1000m	1Gi	2Gi
Data processing batch	2000m	4Gi	8Gi
Tier assignment is owned by the service's primary engineering manager.

Memory limit changes
Increasing a service's memory limit is a temporary measure to buy time, not a fix. Any increase greater than 25% requires:

A linked incident or ticket explaining why
A follow-up to identify the underlying memory issue
Reversion to original limits within 30 days unless permanent change is approved
OOMKill alerts
If a deployment is OOMKilled more than 3 times in 24 hours, an alert fires to the service owner. After 10 OOMKills in a week, the deployment is automatically tagged for review by the platform team.

Exceptions
JVM-based services with documented sawtooth GC patterns may exceed the 2x limit rule with platform-team approval. Document the exception in the service's README.
""",
            },
        ],
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
            "status": S.RESOLVED,
            "priority": P.P2,
            "assignee": "Carlos Ruiz",
            "reporter": "Priya Sharma",
            "days_ago": 42,
            "hour": 4,
        },
        "documents": [
            {
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
                "title": "Log Rotation FAQ",
                "doc_type": "faq",
                "content": """\
# Log Rotation FAQ

## Why didn't logrotate run last night?

Most common causes:

1. `/etc/cron.daily/logrotate` was removed or made non-executable
2. The cron daemon itself isn't running (`systemctl status crond`)
3. A previous logrotate run is still running (`pgrep -a logrotate`) — usually because compression is slow
4. Syntax error in a `/etc/logrotate.d/*` config file — check with `logrotate -d /etc/logrotate.conf`

## What does the .status file actually do?

`/var/lib/logrotate/logrotate.status` records the last rotation time per file. Logrotate uses this to decide "is it time to rotate again?" If the file is missing or unreadable, logrotate assumes "never rotated" and rotates everything immediately — which can spike disk I/O briefly.

## Can I run logrotate manually?

Yes:

```bash
logrotate -f /etc/logrotate.conf
-f forces rotation regardless of the schedule. Useful for emergency disk cleanup. Use -d (dry-run) first to see what would happen without changing files.

What's the difference between compress and delaycompress?
compress runs gzip on the rotated file immediately. delaycompress waits one rotation cycle before compressing. Use delaycompress for log files that the application keeps writing to briefly after rotation.

How do I rotate logs on a sidecar pattern instead?
Use Fluent Bit or Vector as a sidecar container. It tails the application log file and ships to centralized storage. The application's stdout/stderr is captured by the container runtime — no on-disk file to rotate.

Why are some log files not rotating despite being in the config?
The nocreate directive means logrotate won't create a new file after rotating. If the application doesn't reopen its log file (e.g., it caches the file descriptor), it'll keep writing to the rotated file. Add a postrotate block that signals the app (kill -HUP $PID) to reopen.

What size threshold should I use?
For high-traffic services, rotate at 100MB. For low-volume internal services, daily rotation regardless of size is simpler. Avoid rotating at 1GB+ — compression takes too long and blocks the rotation.
""",
            },
            {
                "title": "Log Retention Best Practices Guide",
                "doc_type": "guide",
                "content": """\

Log Retention Best Practices Guide
Why log retention is hard
Logs are the cheapest observability signal to produce but the most expensive to store at scale. A single noisy service can produce 100GB/day; multiply by 50 services and you have 5TB/day. Without retention policy, disk and storage costs grow unbounded.

Three-tier retention strategy
Tier	Storage	Retention	Use case
Hot	Elasticsearch / local disk	7 days	Live incident investigation
Warm	Object storage (S3)	90 days	Trend analysis, compliance
Cold	Glacier / archive	7 years	Audit, legal hold
Each tier costs ~10x less than the previous. Move data through tiers based on age, not access patterns.

What to log (and what not to)
Errors with full stack traces
Request IDs at service boundaries (for distributed tracing correlation)
Authentication / authorization decisions (audit trail)
Slow query times above threshold
Do not log:

Successful health checks (high volume, no value)
Per-row debug data in production
PII unless explicitly required and encrypted at rest
Secrets — ever
Centralized vs sidecar logging
Centralized (rsyslog → Elasticsearch): simpler ops, but a single ingest pipeline can become a SPOF.

Sidecar (Fluent Bit per pod): better isolation, harder to manage at scale. Use sidecar for high-cardinality services where the centralized pipeline can't keep up.

Compression and retention
Compress old logs aggressively. Plain text logs compress at 10-20:1 with gzip. Use delaycompress in logrotate for files that are still being appended.

Index lifecycle management (ILM) in Elasticsearch
Set up ILM policies for every index pattern:

Hot phase: 0-7 days, full replicas, force-merge disabled
Warm phase: 7-30 days, 1 replica, force-merge to 1 segment
Cold phase: 30+ days, 0 replicas, frozen if read-only
Delete phase: 90+ days
Don't rely on manual cleanup — it always falls behind. ILM runs automatically.

Alerting on log volume
Alert when daily volume per service exceeds 2x the 30-day average. Sudden volume spikes usually indicate a bug (debug logging left on, infinite loop) rather than legitimate traffic growth.
""",
            },
        ],
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
            "status": S.IN_PROGRESS,
            "priority": P.P2,
            "assignee": "Rachel Adams",
            "reporter": "Tom Bradley",
            "days_ago": 6,
            "hour": 5,
        },
        "documents": [
            {
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
                "title": "API Rate Limit Tier Policy",
                "doc_type": "policy",
                "content": """\
# API Rate Limit Tier Policy

## Purpose

This policy defines the rate limits enforced at the API gateway for all public-facing APIs. Tiers reflect customer contract obligations and operational guardrails.

## Tier definitions

| Tier | Requests / second | Burst capacity | Daily quota |
|---|---|---|---|
| Free | 50 | 100 | 1,000,000 |
| Pro | 200 | 400 | 50,000,000 |
| Enterprise | 500 | 1,500 | Unlimited |
| Internal (service-to-service) | 2,000 | 5,000 | Unlimited |

Burst capacity = short-term ceiling absorbed via token bucket. Sustained traffic above the per-second limit triggers 429.

## Tier assignment

- Customer tier is determined at signup and stored in customers.tier
- Tier changes during the contract term require Sales + Engineering approval
- Free-tier customers can self-serve upgrade via the dashboard
- Internal services must declare their tier in their deployment manifest

## Customer contract obligations

- **Pro and above**: rate limit headers (X-RateLimit-*) must be returned on every response
- **Enterprise**: SLA of 99.9% availability for the rate-limit-respecting traffic
- **Enterprise**: 24h notice required before any tier limit change

## Operational safeguards

Regardless of tier, every API key is subject to:

- Per-IP cap of 10x the per-key limit (prevents IP-based amplification)
- Global ceiling of 50,000 RPS across all keys (prevents accidental DDoS)
- Geographic anomaly detection — sudden traffic from a new region triggers review

## What happens at the limit

- **At limit**: requests return 429 with Retry-After header
- **Sustained 5min above limit**: customer success notified (Enterprise only)
- **24h sustained pattern**: account flagged for tier review

## Audit

Quarterly review by API platform team. Findings include:

- Any tier overrides not tied to a customer contract
- Configs that don't match contract on file
- Internal services exceeding their declared tier

## Change management

Rate limit config changes require:

1. PR review by API platform team
2. Integration test that verifies new limits via synthetic traffic
3. Customer notification if any tier ceiling is reduced
""",
            },
            {
                "title": "API Rate Limit FAQ",
                "doc_type": "faq",
                "content": """\
# API Rate Limit FAQ

## Why am I getting 429 Too Many Requests?

The gateway returns 429 when your API key exceeds the rate limit for your tier. The response includes:

- X-RateLimit-Limit — your per-second limit
- X-RateLimit-Remaining — requests remaining in the current window
- Retry-After — seconds to wait before retrying

## What's the difference between rate limit and quota?

Rate limit = requests per second (smoothed via burst capacity). Quota = total requests per day or month.

You can hit either independently. A 1000-request burst spread across 10 seconds at 100 RPS may exceed your per-second limit (rate limit 429) without using significant quota.

## How does burst capacity work?

The gateway uses a token bucket. Tokens accumulate at your per-second limit; each request consumes one. When the bucket is full (at burst capacity), excess tokens are discarded.

Concretely for Pro tier (200 RPS / 400 burst): you can send up to 400 requests in one second after a quiet period, then 200 RPS sustained.

## My traffic is uneven — should I retry on 429?

Yes, with exponential backoff. Respect Retry-After. Don't retry immediately — you'll just be rate-limited again.

## Why does my rate limit reset at odd times?

The window is per-API-key and starts when your first request hits the gateway. It's not aligned to wall-clock minutes. If you need predictable reset windows for billing reasons, use quota (daily) not rate (per-second).

## Can I share an API key across multiple servers?

You can, but you're sharing the rate limit. For high-throughput integrations, request a dedicated key per server (Pro and above can have up to 10 keys per account).

## What happens if I exceed my daily quota?

Your account is paused for the rest of the day. You can upgrade tier or contact support to unpause earlier. Enterprise has no daily quota.

## Why did I get a 429 even though I'm well under my limit?

Two reasons:

1. **Per-IP cap**: even if your API key has high limits, the source IP has a 10x cap. If you're behind a NAT shared with other users, you may hit the IP cap.
2. **Global ceiling**: during a DDoS-style traffic spike across the platform, the gateway protects itself by enforcing a global cap. Rare, but possible.

## How do I monitor my rate limit usage?

Use the metrics endpoint at api.company.com/v1/usage. It returns rolling 1h / 24h / 30d windows. Pro and above can also stream usage to their own observability stack via webhook.
""",
            },
        ],
    },
]

parser = argparse.ArgumentParser(
    description="Seed the dev/live DB. Default: tickets-only (fast, no embeddings); --full also re-seeds documents."
)
parser.add_argument(
    "--full",
    action="store_true",
    help="Also wipe + re-seed documents (re-embeds via OpenAI). Default: tickets-only.",
)


def _compute_lifecycle(
    created_at: datetime, status: TicketStatus, priority: TicketPriority, factor: float
) -> tuple[datetime | None, datetime | None, datetime | None]:
    """Compute lifecycle timestamps (started, resolved, closed). Each is None until the ticket has reached that state."""
    rank = STATUS_RANK[status]
    sla = timedelta(hours=SLA_HOURS[priority])
    grace = timedelta(hours=24)

    started_at = created_at + 0.15 * sla if rank >= 1 else None
    resolved_at = created_at + factor * sla if rank >= 2 else None
    closed_at = resolved_at + grace if rank >= 3 and resolved_at is not None else None

    return started_at, resolved_at, closed_at


def _build_ticket(
    service_id: UUID,
    title: str,
    status: TicketStatus,
    priority: TicketPriority,
    created_at: datetime,
    factor: float,
    description: str | None = None,
    assignee: str | None = None,
    reporter: str | None = None,
) -> Ticket:
    """Build lifecycle and ticket construction for seeding of tickets."""
    started_at, resolved_at, closed_at = _compute_lifecycle(created_at, status, priority, factor)
    return Ticket(
        service_id=service_id,
        title=title,
        status=status,
        priority=priority,
        created_at=created_at,
        started_at=started_at,
        resolved_at=resolved_at,
        closed_at=closed_at,
        description=description,
        assignee=assignee,
        reporter=reporter,
    )


async def seed_spread_tickets(session: AsyncSession, service_id_by_name: dict[str, UUID]) -> None:
    """Seed data for spread tickets via ORM."""
    now = datetime.now(UTC)
    for i, row in enumerate(SPREAD_TICKETS):
        days_ago, hour, service_name, status, priority, title = row
        created_at = now - timedelta(days=days_ago, hours=hour)
        factor = 1.2 if i % 7 == 0 else 0.85
        service_id = service_id_by_name[service_name]
        ticket = _build_ticket(
            service_id=service_id,
            title=title,
            status=status,
            priority=priority,
            created_at=created_at,
            factor=factor,
        )
        session.add(ticket)


async def seed_scenario_tickets(session: AsyncSession, service_id_by_name: dict[str, UUID]) -> None:
    """Seed data for scenario tickets via ORM."""
    now = datetime.now(UTC)
    for i, scenario in enumerate(SCENARIOS):
        ticket_data = scenario["ticket"]
        created_at = now - timedelta(days=ticket_data["days_ago"], hours=ticket_data["hour"])
        factor = 1.2 if i % 7 == 0 else 0.85
        ticket = _build_ticket(
            service_id=service_id_by_name[scenario["service"]["name"]],
            title=ticket_data["title"],
            description=ticket_data["description"],
            status=ticket_data["status"],
            priority=ticket_data["priority"],
            assignee=ticket_data["assignee"],
            reporter=ticket_data["reporter"],
            created_at=created_at,
            factor=factor,
        )
        session.add(ticket)


async def ensure_service(session: AsyncSession, service_data: dict[str, Any]) -> UUID:
    """Query Service by name, create if not found.

    ORM query-then-insert.
    """
    stmt = select(Service.id).where(Service.name == service_data["name"])
    service_id: UUID | None = await session.scalar(stmt)

    if service_id is None:
        new_service = Service(**service_data)
        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)
        service_id = new_service.id

    return service_id


async def seed_documents(
    client: AsyncClient,
    service_id: UUID,
    documents_data: list[dict[str, str]],  # without service_id
) -> None:
    """Seed data for documents via existing API POST endpoints."""
    # Inject service_id
    for document_data in documents_data:
        payload_document = {**document_data, "service_id": str(service_id)}

        response_document = await client.post("/api/v1/documents", json=payload_document)
        response_document.raise_for_status()


async def report(full: bool) -> None:
    """Print comparison between source data and actual data written in database."""
    # actual data written
    async with Session() as session:
        actual_total_documents = await session.scalar(select(func.count()).select_from(Document))
        actual_total_tickets = await session.scalar(select(func.count()).select_from(Ticket))
        actual_status_rows = (
            await session.execute(
                select(Ticket.status, func.count()).group_by(Ticket.status).order_by(Ticket.status)
            )
        ).all()
        actual_priority_rows = (
            await session.execute(
                select(Ticket.priority, func.count())
                .group_by(Ticket.priority)
                .order_by(Ticket.priority)
            )
        ).all()
    actual_status = dict(actual_status_rows)
    actual_priority = dict(actual_priority_rows)

    # expected data to write
    expected_total_documents = sum(len(s["documents"]) for s in SCENARIOS) if full else 0
    expected_total_tickets = len(SPREAD_TICKETS) + len(SCENARIOS)
    expected_status = Counter(row[3] for row in SPREAD_TICKETS) + Counter(
        s["ticket"]["status"] for s in SCENARIOS
    )
    expected_priority = Counter(row[4] for row in SPREAD_TICKETS) + Counter(
        s["ticket"]["priority"] for s in SCENARIOS
    )

    # prepare to print
    docs_ok = actual_total_documents == expected_total_documents
    tickets_ok = actual_total_tickets == expected_total_tickets
    status_ok = {st: actual_status.get(st, 0) == expected_status[st] for st in expected_status}
    priority_ok = {
        pr: actual_priority.get(pr, 0) == expected_priority[pr] for pr in expected_priority
    }

    if full:
        docs_total = (
            f"{actual_total_documents} / {expected_total_documents} {'✓' if docs_ok else '✗'}"
        )
    else:
        docs_total = f"{actual_total_documents} (untouched)"
    tickets_total = (
        f"{actual_total_tickets} / {expected_total_tickets} {'✓' if tickets_ok else '✗'}"
    )
    status_line = " | ".join(
        f"{st.value}: {actual_status.get(st, 0)}/{expected_status[st]} {'✓' if status_ok[st] else '✗'}"
        for st in status_ok
    )
    priority_line = " | ".join(
        f"{pr.value}: {actual_priority.get(pr, 0)} / {expected_priority[pr]} {'✓' if priority_ok[pr] else '✗'}"
        for pr in priority_ok
    )

    print(f"""
{"=" * 30}
Seed verification — mode: {"full" if full else "tickets-only"}
  Documents (total):   {docs_total}
  Tickets (total):     {tickets_total}
  Tickets by status:   {status_line}
  Tickets by priority: {priority_line}
{"=" * 30}
""")

    # gate
    checks = [
        *([docs_ok] if full else []),
        tickets_ok,
        *status_ok.values(),
        *priority_ok.values(),
    ]
    if not all(checks):
        raise SystemExit(1)


async def main(full: bool) -> None:
    """Seed data in database based on flag (with '--full' flag: tickets + documents, without flag: only tickets)."""
    service_id_by_name: dict[str, UUID] = {}
    async with Session() as session:
        for scenario in SCENARIOS:
            service_id = await ensure_service(
                session=session,
                service_data=scenario["service"],
            )
            service_id_by_name[scenario["service"]["name"]] = service_id

        await session.execute(delete(Ticket))
        if full:
            await session.execute(delete(Document))

        await seed_scenario_tickets(session, service_id_by_name)
        await seed_spread_tickets(session, service_id_by_name)
        await session.commit()

    if full:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for scenario in SCENARIOS:
                await seed_documents(
                    client=client,
                    service_id=service_id_by_name[scenario["service"]["name"]],
                    documents_data=scenario["documents"],
                )

    await report(full)


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(main(full=args.full))
