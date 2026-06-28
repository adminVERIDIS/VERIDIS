# VERIDIS - Strategie de lancement solo founder

## Contraintes non negociables

- Budget marketing : moins de 500 EUR/mois.
- Ads payantes : 0 EUR jusqu'a 10K EUR MRR.
- Charge solo founder : moins de 10h/semaine.
- Canaux prioritaires : LinkedIn organique, waitlist, webinar, outreach cible, partenariats.
- Tracking : Notion CRM pour pipeline, Loops pour emails, PostHog pour analytics produit/landing.

## Objectifs

| Phase | Periode | Objectif business | KPI principal |
| --- | --- | --- | --- |
| Phase 0 | Semaines -4 a 0 | 200 emails qualifies waitlist | 50 inscrits/semaine |
| Phase 1 | Semaines 1 a 4 | 10 clients payants early-bird | 10 ventes annuelles |
| Phase 2 | Mois 2 a 6 | 50 clients, 300K EUR ARR | MRR, demos, conversion |

## Phase 0 - Pre-lancement

### Semaine -4 : fondation identite

LinkedIn founder profile :

- Banniere : "Fondateur VERIDIS - CSRD simplifiee".
- Headline : "J'aide les DAF a dormir tranquille avant leur echeance CSRD".
- About : story founder, non-expert devenu obsede par la preuve CSRD.
- Featured : lien waitlist, checklist CSRD gratuite, posts les plus performants.

Landing page waitlist :

- URL cible : `veridis.fr/early-access`.
- Headline : "Soyez pret pour la CSRD avant tout le monde".
- Sous-titre : "Analysez votre conformite en 5 minutes. Rejoignez 200+ DAF en liste d'attente."
- Formulaire : email, effectif, secteur, role, echeance estimee, rapport deja disponible oui/non.
- CTA : "Rejoindre la liste - acces prioritaire + -30% early-bird".
- Tracking : PostHog event `waitlist_submit`, Loops tag `early_access`, Notion stage `identified`.

### Semaines -3 a -1 : contenu viralisant

Rythme : 1 post LinkedIn par jour ouvre, 5 posts/semaine.

- Lundi : chiffre ou signal fort.
- Mardi : erreur CSRD a ne pas commettre.
- Mercredi : cas pratique ou rapport anonymise.
- Jeudi : decodeur reglementaire.
- Vendredi : behind the scenes VERIDIS.

Le calendrier pret a publier est dans `scripts/linkedin-content-calendar.json`.

### Routine engagement

- Repondre a tous les commentaires en moins de 60 minutes.
- Envoyer 10 demandes de connexion qualifiees par jour pendant la phase 0.
- Relier chaque post a une action : commentaire, DM, waitlist ou checklist.
- Revoir les performances chaque vendredi a 16:00.

## Phase 1 - Lancement soft

### Semaine 1 : webinar de lancement

Titre : "CSRD 2026 : Les 7 erreurs qui coutent 50K EUR aux entreprises francaises (et comment les eviter)".

Format : 45 minutes de presentation, 10 minutes de Q&A.

Canaux :

- LinkedIn Live pour l'audience.
- Zoom en backup.
- Replay envoye a J+1 via Loops.

Promotion :

- J-14 : annonce LinkedIn + email waitlist.
- J-10 : post "erreur CSRD".
- J-7 : DM aux contacts chauds.
- J-3 : rappel email.
- J-1 : post behind the scenes.
- J+1 : replay + offre early-bird.
- J+5 : rappel 48h avant expiration.

Script complet : `scripts/webinar-script.md`.

Offre :

- Essential : 2,520 EUR/an au lieu de 3,600 EUR/an.
- Professional : 5,040 EUR/an au lieu de 7,200 EUR/an.
- Bonus : onboarding 1-to-1 avec le fondateur.
- Garantie : 30 jours satisfait ou rembourse.
- Limite : 10 places.

### Semaines 2-3 : outreach cible

Cible :

- DAF/CFO, directions finance, responsables RSE.
- Entreprises 250-999 salaries.
- Priorite secteur manufacturier.
- France, puis Belgique/Suisse francophone si le message convertit.

Volume :

- 20 messages/jour.
- 5 jours/semaine.
- 100 contacts/semaine.

Objectifs :

- 35% acceptation connexion.
- 20% reponse positive.
- 8-10% demos bookees.
- 50% conversion demo qualifiee vers client early si douleur forte.

Templates : `scripts/cold-outreach-templates.json`.

Tracking Notion :

- `identified`
- `contacted`
- `connected`
- `replied`
- `demo_booked`
- `diagnostic_sent`
- `trial`
- `paid`
- `lost`

### Semaine 4 : double down

Questions de revue :

- Quel segment repond le plus ?
- Quel post a cree le plus de demos ?
- Quelle objection bloque les ventes ?
- Quel message depasse 20% de reponses positives ?
- Quelle action supprimer parce qu'elle ne convertit pas ?

Decision :

- Doubler les canaux qui convertissent.
- Couper les formats sans signaux apres 2 semaines.
- Transformer chaque client early en cas d'usage anonymise.

## Phase 2 - Croissance mois 2 a 6

### Canal 1 - Contenu educatif, 40% du temps

Newsletter "La CSRD en 5 min" :

- Rythme : 1 email/semaine.
- Objectif : 1,000 abonnes mois 3, 3,000 mois 6.
- KPI : open rate, click rate, demo requests, replies.
- Outil : Loops.

Blog SEO :

- Rythme : 2 articles/semaine.
- Mots-cles cibles : `CSRD entreprise 500 salaries`, `rapport ESRS E1 exemple`, `conformite CSRD checklist`, `CSRD vs reporting RSE`.
- KPI : impressions Search Console, clics organiques, waitlist signups.

LinkedIn :

- Maintenir 5 posts/semaine.
- Objectif : 5,000 followers mois 3, 15,000 mois 6.
- KPI : impressions, taux d'engagement, commentaires qualifiees, demos.

YouTube, a partir du mois 4 :

- Tutoriels courts CSRD et demos VERIDIS.
- Objectif : 1,000 abonnes mois 6.
- KPI : vues qualifiees, clics vers diagnostic, demandes demo.

### Canal 2 - Partenariats strategiques, 30% du temps

#### Cabinets comptables regionaux

Proposition :

- VERIDIS comme outil de diagnostic CSRD recommande a leurs clients.
- Commission : 20% de la premiere annee ou co-branding webinar.
- Offre partenaire : 3 diagnostics clients gratuits pour prouver la valeur.

Approche :

- 20 cabinets identifies.
- 10 messages personnalises.
- 5 rendez-vous.
- 2 partenaires pilotes.

KPI :

- Partner reply rate.
- Partner calls booked.
- Diagnostics clients generes.
- Revenue partenaire.

#### Associations professionnelles

Cibles :

- MEDEF regional.
- DFCG regionale.
- CCI.
- Associations sectorielles industrielles.
- Clubs DAF/RSE.

Proposition :

- Webinar commun "CSRD : verifier les gaps avant l'audit".
- Checklist co-branded.
- Diagnostic anonymise pour les membres.

KPI :

- Webinars acceptes.
- Participants inscrits.
- Waitlist signups.
- Demos post-webinar.

#### Ecoles de commerce

Cibles :

- HEC, ESSEC, EDHEC, ESCP, Audencia, emlyon.

Proposition :

- Cas d'etude VERIDIS sur transformation d'un rapport RSE en diagnostic CSRD.
- Intervention fondateur.
- Stage etudiant pour veille CSRD, analyse rapports, contenu SEO.

KPI :

- Interventions confirmees.
- Etudiants contributeurs.
- Cas d'etude publies.
- Contenus produits.

#### Fintechs, banques, plateformes finance

Proposition :

- Offre conjointe pour clients PME/ETI.
- Diagnostic CSRD comme couche de confiance dans le parcours de financement.
- Integration API a etudier apres mois 6.

KPI :

- Calls partenaires.
- Leads co-generes.
- Pipeline ARR.
- Conversions.

### Canal 3 - Product-led growth, 20% du temps

Programme ambassadeur :

- -20% pour chaque recommandation convertie.
- Cible : clients early et consultants ESG independants.
- KPI : referrals, conversion referrals, ARR attribue.

Template gratuit "Checklist CSRD 2026" :

- Gated, email requis.
- Objectif : 500 telechargements/mois.
- KPI : downloads, email opt-in, demo requests.

Outil gratuit "Calculateur echeance CSRD" :

- Objectif : 1,000 utilisateurs/mois.
- KPI : tool completions, email captures, upgrades vers trial.

API ouverte, mois 6+ :

- Objectif : integrations tierces et distribution technique.
- KPI : API keys, calls, partner leads.

### Canal 4 - Communaute, 10% du temps

Slack/Discord "CSRD Leaders" :

- Cible : DAF, RSE, consultants, experts finance.
- Positionnement : moderation experte, pas pitch permanent.
- KPI : membres actifs, posts/semaine, intros, demos generees.

Meetup mensuel "Petit-dejeuner CSRD" :

- Paris d'abord, regions ensuite.
- 20 personnes max.
- Format discussion, pas de pitch.
- KPI : inscriptions, presence, calls post-event, partenaires identifies.

Retours produit :

- 1 call client/semaine minimum.
- KPI : feedbacks actionnables, bugs critiques, features influencees par clients payants.

## Time budget solo founder

| Activite | Temps/semaine |
| --- | --- |
| LinkedIn posts et engagement | 2h30 |
| Outreach cible | 2h00 |
| Demos et follow-ups | 2h00 |
| Newsletter ou webinar prep | 1h00 |
| Partenariats | 1h00 |
| Revue KPI et iteration | 0h30 |
| Total | 9h00 |

## KPIs par canal

| Canal | KPI principal | Cible | Outil |
| --- | --- | --- | --- |
| LinkedIn organique | Waitlist signups attribues | 50/semaine pre-lancement | PostHog + UTM |
| LinkedIn contenu | Engagement rate | 5% | LinkedIn analytics |
| LinkedIn outreach | Positive reply rate | 20% | Notion CRM |
| Webinar | Clients early-bird | 10 | Stripe + Notion |
| Email waitlist | Click rate vers booking | 12% | Loops |
| Blog SEO | Leads organiques | 100/mois mois 3 | Search Console + PostHog |
| Partenariats | Partner-sourced demos | 10/mois mois 4 | Notion CRM |
| PLG checklist | Telechargements | 500/mois | Loops + PostHog |
| Community | Calls clients/prospects | 4/mois | Notion CRM |

## Tracking events PostHog

- `waitlist_viewed`
- `waitlist_submit`
- `linkedin_post_click`
- `checklist_downloaded`
- `webinar_signup`
- `webinar_replay_clicked`
- `booking_clicked`
- `checkout_started`
- `checkout_completed`
- `diagnostic_uploaded`
- `score_viewed`
- `gap_exported`

## UTM convention

Format :

`utm_source=[linkedin|newsletter|partner|seo]&utm_medium=[organic|email|referral]&utm_campaign=[phase_channel_week]&utm_content=[asset_or_post_type]`

Exemples :

- `utm_source=linkedin&utm_medium=organic&utm_campaign=prelaunch_week_1&utm_content=stat_post`
- `utm_source=linkedin&utm_medium=dm&utm_campaign=soft_launch_outreach&utm_content=first_message`
- `utm_source=partner&utm_medium=referral&utm_campaign=cabinet_webinar&utm_content=co_branded_checklist`

## Revue hebdomadaire

Chaque vendredi a 16:00 :

1. Exporter les KPI LinkedIn, Loops, PostHog, Notion.
2. Identifier le contenu qui a cree des conversations qualifiees.
3. Identifier l'outreach qui a cree des demos.
4. Couper les angles sans signaux.
5. Choisir une action a doubler la semaine suivante.

## Sources reglementaires a verifier avant publication

Les contenus commerciaux doivent eviter les promesses juridiques et verifier les calendriers avant publication :

- Commission europeenne : `https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en`
- EUR-Lex, directive stop-the-clock : `https://eur-lex.europa.eu/eli/dir/2025/794/oj`
- AMF : `https://www.amf-france.org/`

## Commentaires apres plan

- Garder le message principal sur la preuve, les gaps et l'auditabilite. Les calendriers peuvent bouger, la douleur operationnelle reste.
- Ne pas multiplier les canaux avant 10K EUR MRR. LinkedIn, webinar, outreach et partenariats suffisent.
- Chaque client early doit devenir un partenaire produit : onboarding fondateur, feedback structure, cas anonymise, potentiel ambassadeur.
