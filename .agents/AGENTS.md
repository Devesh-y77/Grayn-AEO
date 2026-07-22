## Security and Credentials
- NEVER write credentials into any file outside `.env` itself — no scratch files, no backups, no debug dumps.
- If you need to restore or move credentials, print instructions for the user to do it manually.
- Any credential-related accident must be reported to the user as its own message immediately, not as a clause inside a status update.
