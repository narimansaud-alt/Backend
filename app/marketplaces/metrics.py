from prometheus_client import Counter, Gauge, Histogram

SYNC_JOBS = Counter(
    "marketplace_sync_jobs_total",
    "Marketplace synchronization jobs by terminal state.",
    ("marketplace", "kind", "status"),
)
SYNC_DURATION = Histogram(
    "marketplace_sync_job_duration_seconds",
    "Marketplace synchronization job duration.",
    ("marketplace", "kind"),
)
SYNC_IN_PROGRESS = Gauge(
    "marketplace_sync_jobs_in_progress",
    "Synchronization jobs currently executing in this worker process.",
    ("marketplace", "kind"),
)
SYNC_API_ERRORS = Counter(
    "marketplace_sync_api_errors_total",
    "Marketplace HTTP errors observed by connectors.",
    ("marketplace", "status"),
)
SYNC_RECORDS = Counter(
    "marketplace_sync_records_upserted_total",
    "Normalized records sent to idempotent upsert.",
    ("marketplace", "kind"),
)
SYNC_LAST_SUCCESS = Gauge(
    "marketplace_sync_last_success_timestamp_seconds",
    "Unix timestamp of the last successful synchronization.",
    ("marketplace", "kind", "cabinet_id"),
)
