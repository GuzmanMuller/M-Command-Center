# Security

MCC 0.2 is a pre-release local viewer, not a public service. No remote exposure or reverse proxy is supported. Local programs running as your user can read your credential; protect your account, config and data directories. Store directories on trusted owner-controlled filesystems. Authentication is not a sandbox against a compromised local account.

Send vulnerabilities privately to the repository owner using a verified private contact or GitHub private vulnerability reporting when enabled. Do not post credentials or real snapshots in issues. There is no public security mailbox configured in this candidate.

Login is rate-limited to ten attempts per minute in process memory. Sessions expire in one hour and on restart. Token rotation takes effect on restart. Unsupported mutation paths return 405; there are no execution capabilities. Invalid snapshot data fails closed. Never import unreviewed private tracker data. Report malformed request denial-of-service and file-race findings privately.

Support policy: only reviewed releases are supported; this candidate has no released support window yet.
