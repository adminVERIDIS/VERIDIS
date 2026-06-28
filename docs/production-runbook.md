# VERIDIS production runbook

## Architecture

- Cloudflare: DNS, CDN, WAF, DDoS, SSL universel.
- Vercel: frontend Next.js dans `apps/web`, Analytics et Speed Insights.
- Railway ou Render: API FastAPI via `apps/api/Dockerfile`, 2 instances API, 1 worker, 1 beat.
- Services manages: PostgreSQL, Redis, S3 Scaleway, Sentry, PostHog, UptimeRobot.

## Deploy

### Frontend

1. Configurer les secrets GitHub: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
2. Configurer les variables Vercel de `apps/web/.env.production.example`.
3. Push sur `main`; le workflow `.github/workflows/deploy.yml` lance tests, build puis `vercel deploy --prebuilt --prod`.

### API

1. Creer le service Railway `veridis-api`.
2. Configurer `RAILWAY_TOKEN` dans GitHub.
3. Configurer les variables de `.env.production.example` dans Railway.
4. Le workflow publie `apps/api` avec le `Dockerfile`.

### VPS fallback

```bash
cp .env.production.example .env.production
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build --scale api=2
```

## Health checks

- Web: `GET https://veridis.fr/api/health`
- API: `GET https://api.veridis.fr/health`
- API detaille: `GET https://api.veridis.fr/health/detailed`

`/health/detailed` retourne `ok`, `degraded` ou `skipped` par dependance.

## Backups

Planifier toutes les nuits:

```bash
DATABASE_URL=... REDIS_URL=... S3_BACKUP_BUCKET=s3://veridis-backups SLACK_WEBHOOK_URL=... ./scripts/backup.sh
```

Le script cree:

- `postgres.sql.gz`
- `redis.rdb` si `REDIS_URL` et `redis-cli` sont disponibles
- upload S3 horodate
- retention 30 jours par defaut
- notification Slack

## Recovery test

1. Telecharger le dernier backup:

```bash
aws s3 sync s3://veridis-backups/20260628_020000/ /tmp/veridis-restore/
```

2. Restaurer PostgreSQL dans une base de test:

```bash
gunzip -c /tmp/veridis-restore/postgres.sql.gz | psql "$RESTORE_DATABASE_URL"
```

3. Restaurer Redis si necessaire:

```bash
redis-cli -u "$RESTORE_REDIS_URL" --rdb /tmp/veridis-restore/redis.rdb
```

4. Lancer `/health/detailed` sur l'environnement restaure.

## Monitoring

Planifier `scripts/monitor.sh` toutes les 5 minutes ou configurer UptimeRobot sur les memes endpoints.

```bash
SLACK_WEBHOOK_URL=... ./scripts/monitor.sh
```

## Cost target

- Vercel Pro: 20 EUR/mois
- Railway/Render API: 50-100 EUR/mois
- PostgreSQL: 25-50 EUR/mois
- Redis: 10-20 EUR/mois
- S3 Scaleway: 5-10 EUR/mois
- Cloudflare Pro: 20 EUR/mois
- Sentry + PostHog: 30-50 EUR/mois

Total attendu: 160-270 EUR/mois au lancement, sous 500 EUR/mois a 1000 clients avec scaling horizontal controle.
