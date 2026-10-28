# Data provenance

All three bundled files are synthetic and authored for SupportIQ:

- `complaints.csv`: 144 English narratives, six classes, explicit train/validation/test splits.
- `tickets.json`: 18 fictional demonstration conversations with relative age in hours.
- `policies.json`: 12 fictional policies designed to exercise retrieval and review.

Reproduce them with `python scripts/create_demo_data.py`. This overwrites these three fixture files; it does not edit a running application's database.

No real CFPB narrative or actual customer information is included. `scripts/import_cfpb.py` prepares a user-downloaded export separately. Imported `cfpb*.csv` and metadata files are ignored by Git and Docker to avoid accidental redistribution. Do not commit customer data.

The urgency deadlines in the app are demonstration service targets, not legal deadlines. Policy text must be replaced and reviewed before a real deployment.
