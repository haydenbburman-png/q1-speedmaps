#!/bin/sh
# Registers a systemd user timer that rebuilds the speedmaps 3x a day (Linux), at the same
# times as schedule_windows.ps1. Persistent=true runs a missed build when the machine comes back on.
# Run once from the project folder:  sh scripts/schedule_linux.sh
# Check:   systemctl --user list-timers q1-speedmaps.timer
# Remove:  systemctl --user disable --now q1-speedmaps.timer
set -e
root=$(cd "$(dirname "$0")/.." && pwd)
units="$HOME/.config/systemd/user"
mkdir -p "$units" "$root/output"

cat > "$units/q1-speedmaps.service" <<EOF
[Unit]
Description=Build Q1 Lakeside speedmaps

[Service]
Type=oneshot
WorkingDirectory=$root
ExecStart=/bin/sh "$root/scripts/run_speedmaps.sh"
EOF

cat > "$units/q1-speedmaps.timer" <<EOF
[Unit]
Description=Q1 Lakeside speedmaps at 9:00, 12:30 and 16:30 Brisbane time

[Timer]
OnCalendar=*-*-* 09:00:00 Australia/Brisbane
OnCalendar=*-*-* 12:30:00 Australia/Brisbane
OnCalendar=*-*-* 16:30:00 Australia/Brisbane
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now q1-speedmaps.timer
echo "Scheduled. Output: $root/output/latest.html (log: $root/output/run_log.txt)"
