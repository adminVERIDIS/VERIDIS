# VERIDIS - Playbook de Vente Solo Founder

## Principes

- Pas de quota artificiel.
- Pas de pression manipulative.
- Chaque prospect est un partenaire potentiel : feedback, referral, temoignage.
- La transparence bat le bluff.
- Le long terme bat le short term.
- Objectif : 20% conversion call vers payant, 50% sur prospects early-stage avec early-bird.

## Stack

| Outil | Usage |
| --- | --- |
| Notion | CRM simple, pipeline, notes, follow-ups |
| Calendly | Booking calls site + emails |
| Loom | Demos asynchrones |
| Stripe | Checkout en direct |

## Funnel 7 etapes

| Etape | Objectif | Sortie attendue | Conversion cible |
| --- | --- | --- | --- |
| Lead | Identifier source et contexte | Fiche CRM | 100% |
| Qualif | BANT rapide | Call ou nurture | 60% |
| Discovery | Comprendre douleurs | Demo pertinente | 40% |
| Demo | Montrer valeur | Plan recommande | 30% |
| Proposition | Cadrer offre | Decision ou objection | 25% |
| Close | Reduire risque | Stripe ou next step | 20% |
| Onboarding | Premier succes | Activation 24h | 18% |

## Etape 1 - Lead

Sources :

- inbound : waitlist, contenu, SEO, referral ;
- outbound : LinkedIn Sales Navigator, cold email, partenariats ;
- events : webinar, community, associations.

Qualification rapide :

- Budget : avez-vous un budget alloue pour la conformite CSRD ?
- Authority : etes-vous la personne qui porte ou decide le sujet ?
- Need : avez-vous deja commence votre rapport CSRD ?
- Timing : quelle est votre date d'echeance ou prochaine revue ?

Decision :

- BANT positif : call 20-30 minutes.
- BANT negatif : nurture newsletter + relance 30 jours.

## Etape 2 - Call qualif 10 minutes

Script :

> Bonjour {{prenom}}, merci pour votre interet pour VERIDIS.
>
> En 2 minutes : ou en etes-vous sur la CSRD ?

Ecouter. Ne pas vendre.

Puis :

> Ok, voici ce que je propose : un call de 30 minutes ou je vous montre comment VERIDIS analyse un rapport CSRD en direct. A la fin, vous saurez exactement ou vous en etes et quelles sont vos priorites.
>
> Ca vous dit jeudi 14h ou vendredi 10h ?

## Etape 3 - Call decouverte 30 minutes

Fichier detaille : `scripts/sales-discovery-call-script.md`.

Objectif : comprendre situation, douleurs, impact, urgence douce.

Regle : ecouter 80%, parler 20%.

## Etape 4 - Demo

Regles d'or :

- Jamais de demo generique.
- Toujours personnalisee au secteur ou a la taille.
- Commencer par le probleme, pas par les features.
- Laisser le prospect cliquer quand possible.
- Garder le silence apres le resultat.

Script court :

> Je vais prendre un rapport RSE du secteur {{secteur}}, similaire a ce que vous pourriez avoir.
>
> Voila ce que VERIDIS a trouve en quelques minutes.
>
> Score global : {{score}}/100. Categorie : {{categorie}}.
>
> Vos trois priorites : {{gap_1}}, {{gap_2}}, {{gap_3}}.
>
> Chaque gap a un guide pas a pas. Pas besoin d'etre expert ESG pour savoir quoi faire ensuite.

## Etape 5 - Proposition

Recommandation :

- Essential : 250-499 salaries, perimetre simple, premiere evaluation.
- Professional : 500-999 salaries, multi-sites, benchmark, plusieurs utilisateurs.
- Enterprise : 1000+ salaries, gouvernance avancee, API, white-label, SLA.

Prix :

| Plan | Prix public | Early-bird -30% |
| --- | --- | --- |
| Essential | 3 600 EUR/an | 2 520 EUR/an |
| Professional | 7 200 EUR/an | 5 040 EUR/an |
| Enterprise | 14 400 EUR/an | 10 080 EUR/an |

Script :

> Base sur ce qu'on a vu, voici ce que je recommande : {{plan}}.
>
> Prix : {{prix}} EUR/an, soit {{prix_mensuel}} EUR/mois en equivalent.
>
> Ce qui est inclus : {{features_pertinentes}}.
>
> Ce qui n'est pas inclus : {{limitations}}.
>
> Si vous decidez d'ici {{date}}, l'early-bird est de -30% la premiere annee.
>
> Garantie : 30 jours satisfait ou rembourse.
>
> Vous avez besoin de reflechir, ou vous avez des questions maintenant ?

## Etape 6 - Close

Phrase :

> On fait comme ca : je vous envoie le lien Stripe maintenant, vous avez 14 jours pour tester. Si a J+14 vous n'etes pas convaincu, je vous rembourse, et on reste en contact pour la suite.
>
> Ca vous va ?

Si objection : utiliser `scripts/objection-handling-cheat-sheet.md`.

## Etape 7 - Onboarding immediat

Script :

> Super, bienvenue.
>
> Voici ce qui se passe maintenant :
>
> Aujourd'hui, vous accedez au dashboard.
>
> Aujourd'hui, vous uploadez votre rapport et lancez la premiere analyse.
>
> Demain, je vous appelle pour voir les resultats et repondre a vos questions.
>
> Cette semaine, on fait le point sur vos 3 priorites.
>
> Votre premier succes avec VERIDIS : avoir votre score de conformite et votre plan d'action en 24h.

## Fichiers operationnels

- `scripts/crm-notion-template.json` : template CRM Notion.
- `scripts/sales-discovery-call-script.md` : call decouverte minute par minute.
- `scripts/demo-script-looom.md` : demo Loom asynchrone.
- `scripts/objection-handling-cheat-sheet.md` : 18 objections et reponses.
- `scripts/post-call-email-templates.json` : emails merci, proposition, relance, onboarding.
- `scripts/sales-call-quality-checklist.md` : auto-evaluation apres call.

## Rythme hebdomadaire

| Activite | Volume |
| --- | --- |
| Revue actions Notion | 5 fois/semaine |
| Outreach qualifie | 20/jour |
| Calls decouverte | 5-10/semaine |
| Demos Loom | 3-5/semaine |
| Relances post-call | Tous les jours |
| Revue pipeline | Vendredi 16h |

## KPIs

| KPI | Cible |
| --- | --- |
| Lead vers qualifie | 60% |
| Qualifie vers discovery | 40% |
| Discovery vers demo | 75% |
| Demo vers proposition | 80% |
| Proposition vers close | 50% |
| Call vers payant | 20% |
| Early-stage avec early-bird | 50% |

## Commentaire apres playbook

Le playbook doit rester vivant. Chaque objection entendue deux fois doit etre ajoutee a la cheat sheet. Chaque email qui obtient une reponse doit devenir le nouveau standard.
