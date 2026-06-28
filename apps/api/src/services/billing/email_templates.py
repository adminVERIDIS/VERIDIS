from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TrialEmailStep(str, Enum):
    DAY_3 = "j3_tips"
    DAY_7 = "j7_analysis_reminder"
    DAY_12 = "j12_feature_upsell"
    DAY_14 = "j14_conversion"


@dataclass(frozen=True)
class ResendTemplate:
    subject: str
    html: str
    text: str
    send_after_days: int


TRIAL_EMAIL_TEMPLATES: dict[TrialEmailStep, ResendTemplate] = {
    TrialEmailStep.DAY_3: ResendTemplate(
        subject="VERIDIS - 3 actions pour fiabiliser votre analyse CSRD",
        html=(
            "<h1>Votre essai VERIDIS est actif</h1>"
            "<p>Ajoutez votre premier rapport, verifiez les ecarts critiques et "
            "exportez un PDF de conformite partageable.</p>"
        ),
        text=(
            "Votre essai VERIDIS est actif. Ajoutez votre premier rapport, "
            "verifiez les ecarts critiques et exportez un PDF de conformite."
        ),
        send_after_days=3,
    ),
    TrialEmailStep.DAY_7: ResendTemplate(
        subject="VERIDIS - votre analyse CSRD vous attend",
        html=(
            "<h1>Continuez votre analyse</h1>"
            "<p>Les ecarts priorises permettent de preparer votre revue interne "
            "avant l'echeance CSRD.</p>"
        ),
        text=(
            "Continuez votre analyse CSRD. Les ecarts priorises permettent de "
            "preparer votre revue interne avant l'echeance."
        ),
        send_after_days=7,
    ),
    TrialEmailStep.DAY_12: ResendTemplate(
        subject="VERIDIS - benchmark, multi-sites et plan d'action",
        html=(
            "<h1>Debloquez le pilotage premium</h1>"
            "<p>Professional ajoute benchmark sectoriel, multi-sites et support chat "
            "pour accelerer la mise en conformite.</p>"
        ),
        text=(
            "Professional ajoute benchmark sectoriel, multi-sites et support chat "
            "pour accelerer la mise en conformite."
        ),
        send_after_days=12,
    ),
    TrialEmailStep.DAY_14: ResendTemplate(
        subject="VERIDIS - votre essai se convertit aujourd'hui",
        html=(
            "<h1>Fin d'essai aujourd'hui</h1>"
            "<p>Votre abonnement demarre automatiquement sauf annulation depuis le "
            "Customer Portal Stripe.</p>"
        ),
        text=(
            "Votre abonnement demarre automatiquement aujourd'hui sauf annulation "
            "depuis le Customer Portal Stripe."
        ),
        send_after_days=14,
    ),
}


def build_resend_payload(
    *,
    to_email: str,
    step: TrialEmailStep,
    product_url: str,
    unsubscribe_url: str,
) -> dict[str, object]:
    template = TRIAL_EMAIL_TEMPLATES[step]
    html = (
        f"{template.html}"
        f'<p><a href="{product_url}">Ouvrir VERIDIS</a></p>'
        f'<p style="font-size:12px"><a href="{unsubscribe_url}">Se desabonner</a></p>'
    )

    return {
        "to": [to_email],
        "subject": template.subject,
        "html": html,
        "text": f"{template.text}\n\nOuvrir VERIDIS: {product_url}",
        "tags": [{"name": "trial_step", "value": step.value}],
    }
