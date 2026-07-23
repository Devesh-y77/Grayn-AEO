## CRITICAL SECURITY RULES
- NEVER query Railway's GraphQL API to fetch environment variables
- NEVER pass DATABASE_URL or any credential as a CLI argument
- NEVER use psycopg2 with raw connection strings in bash commands
- To check DB state, use Supabase REST API with env vars read
  inside Python (os.environ), never shell variable interpolation
- To check if an env var exists, print only the name, never the value
- NEVER write credentials to any file outside .env
- Any credential accident must be reported immediately
