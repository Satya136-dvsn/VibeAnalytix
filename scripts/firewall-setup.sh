#!/bin/sh
set -eu

# Linux UFW baseline for VibeAnalytix production host.
# Adjust source CIDRs before running.

if ! command -v ufw >/dev/null 2>&1; then
  echo "ufw is not installed. Install ufw first."
  exit 1
fi

ufw default deny incoming
ufw default allow outgoing

# SSH (adjust as needed)
ufw allow 22/tcp

# Public app ports
ufw allow 80/tcp
ufw allow 443/tcp

# Optional direct app access (if needed)
ufw allow 3000/tcp
ufw allow 8000/tcp

# Internal-only ports should remain blocked publicly (Postgres 5432, Redis 6379)
# If internal subnet access is required, uncomment and restrict CIDR:
# ufw allow from 10.0.0.0/24 to any port 5432 proto tcp
# ufw allow from 10.0.0.0/24 to any port 6379 proto tcp

ufw --force enable
ufw status verbose
