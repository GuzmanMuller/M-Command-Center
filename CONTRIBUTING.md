# Contributing

Use synthetic fixtures only. Never include live trackers, secrets, database files, machine inventory, telemetry, private URLs or screenshots containing personal data. No live Gateway is needed.

Run `python -m unittest discover -s tests -v`. Changes must preserve read-only HTTP routes, explicit roots, escaping and auth boundaries. Add regression tests and provenance for every retained third-party asset or source. Do not add execution or remote access as an incidental enhancement. Review dependency and action pins before changing them.
