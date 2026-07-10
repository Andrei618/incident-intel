"""Hand-authored fixture data for the RAG eval (documents, tickets)."""

from datetime import date

DOCUMENTS = [
    # --- payment-service
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
        "service": "payment-service",
        "doc_key": "payment-db-pool-sizing-guide",
        "title": "Database Connection Pool Sizing Guide",
        "doc_type": "guide",
        "content": """\
# Database Connection Pool Sizing Guide

## Purpose
How to choose connection pool settings for services that talk to PostgreSQL.
This is a design-time guide — for diagnosing an active pool-exhaustion
incident, see the Payment Service DB Connection Pool Troubleshooting runbook.

## Sizing rules
- Start from measured load: pool_size ≈ peak requests per second x average
  query duration in seconds, rounded up. Do not guess.
- Set max_overflow to 25-50% of pool_size to absorb short bursts.
- pool_timeout controls how long a request waits for a free connection
  before failing; keep it below your upstream request timeout.
- The sum of pool_size + max_overflow across ALL replicas must stay under
  PostgreSQL max_connections, with ~20% headroom reserved for admin
  sessions and migrations.

## Worked example
payment-service at 300 rps peak with 40 ms average query time keeps ~12
connections busy. pool_size=20, max_overflow=10 covers bursts while three
replicas stay within a max_connections of 120.

## When to revisit
Re-run the sizing math after adding replicas, when query latency grows, or
when total demand approaches max_connections — at that point consider
PgBouncer instead of ever-larger pools.
""",
    },
    {
        "service": "payment-service",
        "doc_key": "payment-db-faq",
        "title": "Payment Service Database FAQ",
        "doc_type": "faq",
        "content": """\
# Payment Service Database FAQ

## Who owns the payments database?
The payments platform team owns the schema and capacity planning.
Day-to-day questions go to the #payments-db channel.

## How do I get read access?
Request a read-only role through the access portal. Direct superuser
access is never granted; analysts should use the reporting replica.

## I occasionally see timeout errors in my logs. Is that an incident?
Short blips during deploys are normal — pods reconnect within seconds.
Sustained "connection pool exhausted" errors or a rising 503 rate on
checkout IS an incident: follow the Payment Service DB Connection Pool
Troubleshooting runbook.

## Are idle connections cleaned up automatically?
Yes. Connections idle for more than 5 minutes are terminated by a
scheduled job, so a leaked session cannot hold a connection slot forever.

## How do I request a schema change?
Open a migration PR against the payments repo. The platform team reviews
it and applies it during a maintenance window.

## The database itself seems down. Who do I page?
Page the DBA on-call. Attach recent pg_stat_activity output if you can
still get it.
""",
    },
    # --- api-gateway
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
        "service": "api-gateway",
        "doc_key": "api-gateway-rate-limit-tier-policy",
        "title": "API Rate Limit Tier Policy",
        "doc_type": "policy",
        "content": """\
# API Rate Limit Tier Policy

## Purpose
Defines which request limits apply to which API clients. This is the
policy of record — for diagnosing legitimate requests being rejected
with 429 errors, see the API Gateway Rate Limit Configuration runbook.

## Tiers
- Free tier: 60 requests per minute, burst up to 100. No SLA.
- Standard tier: 600 requests per minute, burst up to 1,000.
- Enterprise tier: negotiated per contract; floor of 6,000 requests
  per minute with dedicated gateway capacity.

## Enforcement
Limits are enforced per API key using a sliding-window counter at the
gateway. Exceeding the window returns HTTP 429 with a Retry-After
header. Repeated abuse (10x the tier limit) triggers a temporary key
suspension and a notification to the account owner.

## Changing a client's tier
Tier assignment is owned by the client's account manager. Upgrades
require a capacity review by the platform team before the new limit is
applied at the gateway. Emergency limit raises during an incident must
be reverted or formalized within five business days.

## Review
This policy is reviewed quarterly against gateway capacity reports.
""",
    },
    {
        "service": "api-gateway",
        "doc_key": "api-gateway-rate-limit-faq",
        "title": "API Rate Limit FAQ",
        "doc_type": "faq",
        "content": """\
# API Rate Limit FAQ

## Why am I getting 429 Too Many Requests?
Your API key exceeded its tier's request limit. Check the Retry-After
header and back off before retrying. If you believe the volume is
legitimate and within your tier, this may be a gateway misconfiguration —
report it so the API Gateway Rate Limit Configuration runbook can be
applied.

## What is my current limit?
Limits are set per tier (free, standard, enterprise) — see the API Rate
Limit Tier Policy. Your current tier is shown in the developer portal
under your API key settings.

## How do I request a higher limit?
Contact your account manager to start a tier upgrade. Capacity review
usually takes two business days. Do not create additional API keys to
work around limits — keys are per client, and abuse triggers suspension.

## Do retries count against my limit?
Yes. Every request that reaches the gateway counts, including retries
and failed requests. Use exponential backoff to avoid burning your
burst allowance.

## Are limits shared across environments?
No. Sandbox keys have separate, lower limits and are not suitable for
load testing.
""",
    },
    # --- auth-service
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
        "service": "auth-service",
        "doc_key": "auth-memory-profiling-guide",
        "title": "Memory Profiling Guide for JVM Services",
        "doc_type": "guide",
        "content": """\
# Memory Profiling Guide for JVM Services

## Purpose
How to capture and read memory profiles for JVM-based services. This is
a skills guide for routine analysis — if pods are actively restarting
with OOMKilled, follow the Auth Service Memory Troubleshooting runbook
first and profile afterwards.

## Capturing a heap dump
- On-demand: jmap -dump:live,format=b,file=/tmp/heap.hprof <pid>
- On crash: set -XX:+HeapDumpOnOutOfMemoryError so the JVM writes a
  dump automatically before the container dies.
- Copy dumps off the pod immediately — they do not survive a restart.

## Reading the dump
Open the .hprof file in Eclipse MAT or VisualVM. Start with the
dominator tree: the biggest retained sizes point to what is holding
memory. A steadily growing collection (often a cache or listener list)
is the classic signature of a memory leak.

## Continuous profiling
For gradual growth that never OOMs, compare two dumps taken hours
apart rather than staring at one. Delta analysis shows which objects
accumulated between snapshots.

## Interpreting limits
Remember the JVM heap is only part of container memory — metaspace,
threads, and off-heap buffers count toward the pod's limit too. Sizing
rules live in the Service Resource Limits Policy.
""",
    },
    {
        "service": "auth-service",
        "doc_key": "auth-resource-limits-policy",
        "title": "Service Resource Limits Policy",
        "doc_type": "policy",
        "content": """\
# Service Resource Limits Policy

## Purpose
Rules for setting container CPU and memory limits on production
services. This is the policy of record — for pods that are actively
OOMKilled, see the Auth Service Memory Troubleshooting runbook.

## Memory rules
- Every production container MUST declare both a memory request and a
  memory limit. Unbounded containers are rejected at deploy time.
- The memory limit must be at least 25% above observed steady-state
  usage, measured over one week of production traffic.
- For JVM services, the heap must be capped at 75% of the container
  limit — metaspace, threads, and off-heap buffers need the rest.

## CPU rules
- CPU requests reflect steady-state usage; CPU limits are discouraged
  (throttling hurts latency more than contention does).

## Raising a limit
A limit increase requires a capacity ticket with a heap analysis
attached — see the Memory Profiling Guide for how to produce one.
Raising a limit to silence OOMKilled restarts without a leak analysis
is explicitly forbidden: it postpones the incident, it does not fix it.

## Review
Limits are re-baselined quarterly from resource usage reports.
""",
    },
    # --- monitoring
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
        "service": "monitoring",
        "doc_key": "monitoring-log-rotation-faq",
        "title": "Log Rotation FAQ",
        "doc_type": "faq",
        "content": """\
# Log Rotation FAQ

## How is log rotation configured?
Via logrotate, driven by a daily cron job. Per-service configs live in
/etc/logrotate.d/. The default policy rotates at 100 MB or daily,
whichever comes first, keeping 7 compressed generations.

## How do I add rotation for a new log file?
Drop a config into /etc/logrotate.d/ in your deploy manifest. Test it
with logrotate -d (dry run) before shipping — a typo silently disables
rotation for that file.

## Why is my log file huge even though rotation is configured?
The usual suspects: the config references the wrong path, the file
matched a `nocreate` rule after the service was renamed, or the cron
job itself is not running. If disk usage is already at critical levels,
switch to the Disk Space Management Guide — that is an incident, not a
configuration question.

## Do rotated logs count against disk quota?
Yes, until the retention window expires. Compression reduces them
roughly 10x. Retention periods are covered in the Log Retention Best
Practices Guide.

## Where do application logs go after rotation?
Compressed generations stay on the host; the log shipper has already
forwarded content to central storage, so local generations are purely
a safety net.
""",
    },
    {
        "service": "monitoring",
        "doc_key": "monitoring-log-retention-guide",
        "title": "Log Retention Best Practices Guide",
        "doc_type": "guide",
        "content": """\
# Log Retention Best Practices Guide

## Purpose
How long to keep logs, where, and why. This is a planning guide — if a
host is already at critical disk usage, follow the Disk Space
Management Guide instead of tuning retention mid-incident.

## Retention tiers
- Hot (searchable, central storage): 14 days for application logs,
  30 days for access logs.
- Warm (compressed object storage): 90 days, restorable within hours.
- Cold (compliance archive): 13 months for auth and payment audit
  trails, per the security baseline.

## Local host retention
Hosts keep only the rotated, compressed generations as a safety net —
see the Log Rotation FAQ for the mechanics. Local retention should
never exceed 7 generations; the log shipper is the source of truth,
not the host's disk.

## Sizing the budget
Estimate: daily log volume x compression factor x retention days per
tier. Re-estimate after enabling debug logging anywhere — one service
at debug level can triple daily volume and quietly eat the disk
headroom that rotation assumes.

## Deleting early
Retention shortening requires sign-off from security (audit logs) or
the service owner (application logs). Deleting logs to free disk space
during an incident is a last resort and must be logged in the incident
timeline.
""",
    },
    # --- infra-vpn
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
    {
        "service": "infra-vpn",
        "doc_key": "vpn-cert-renewal-policy",
        "title": "Certificate Renewal Policy",
        "doc_type": "policy",
        "content": """\
# Certificate Renewal Policy

## Purpose
Rules governing TLS certificate lifetimes and renewal across
infrastructure. This is the policy of record — for an already-expired
certificate breaking connections, execute the VPN Certificate Renewal
Runbook immediately and file the policy review afterwards.

## Lifetime rules
- Public-facing TLS certificates: 90-day lifetime, auto-renewed via
  ACME at two-thirds of lifetime.
- Internal service certificates: 1-year lifetime, auto-renewed by the
  internal CA.
- VPN gateway certificates: 1-year lifetime. Renewal is MANUAL until
  the gateway appliance supports ACME — this exception is the reason
  the VPN runbook exists.

## Monitoring requirements
Every certificate must be registered in the expiry dashboard. Alerts
fire at 30, 14, and 7 days before expiry to the owning team's
channel. An expired production certificate is automatically a SEV-2.

## Ownership
Each certificate has a named owning team. Certificates without an
owner are treated as policy violations and escalated at the quarterly
review.

## Manual renewals
Any certificate that cannot auto-renew must have a documented runbook
and a calendar reminder at 30 days before expiry, reviewed quarterly.
""",
    },
    {
        "service": "infra-vpn",
        "doc_key": "vpn-access-faq",
        "title": "VPN Access FAQ",
        "doc_type": "faq",
        "content": """\
# VPN Access FAQ

## I can't connect to the VPN. Is it broken?
Check the status page first. If only YOU are affected, it is almost
always local: wrong password, expired MFA enrollment, or a stale
client. If EVERYONE is failing to connect at once, that is an incident
— typically an expired gateway certificate; see the VPN Certificate
Renewal Runbook.

## The VPN was just fixed but I still can't connect.
Your client may have cached the old certificate. Restart the VPN
client to clear its cache before reporting a problem.

## Why was I disconnected after 8 hours?
Session lifetime is capped at 8 hours by policy. Reconnect and you
will get a fresh session.

## How do I set up the VPN on a new laptop?
Install the client from the self-service portal and enroll the device
in MFA. Certificates are provisioned automatically at first login —
you never need to install one manually.

## Which traffic goes through the VPN?
Split tunneling is enabled: only internal ranges route through the
gateway. Streaming and general browsing use your normal connection,
so do not report slow YouTube as a VPN incident.
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
