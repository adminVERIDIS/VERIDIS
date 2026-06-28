# Dashboard analytics fondateur

## Route web

- Page: `apps/web/app/(admin)/analytics/page.tsx`
- Polling: `GET /api/analytics/dashboard?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`, refresh 30 secondes.
- Drill-down: les cartes, etapes funnel et actions clients exposent le contexte selectionne pour brancher une liste paginee.

## API

- `AnalyticsRouter.get_mrr(start_date, end_date, granularity)`
- `AnalyticsRouter.get_funnel(start_date, end_date)`
- `AnalyticsRouter.list_customers(status, plan, search, sort_by, sort_order, page, page_size)`
- `AnalyticsRouter.get_active_alerts()`

Le montage HTTP doit rester admin-only. Le routeur est volontairement sans dependance FastAPI pour respecter le backend actuel; il peut etre appele depuis un endpoint FastAPI, Next API proxy ou worker interne.

## Jobs recommandes

- MRR: recalcul horaire, cache 5 minutes.
- Funnel: materialized view rafraichie toutes les 4 heures.
- Alertes: `AlertEngine.evaluate_all()` toutes les heures, email pour `critical`, Slack pour toutes les alertes.
