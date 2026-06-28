import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import Stripe from "stripe";

import { findPlanByPriceId } from "../../../../lib/billing/pricing";

function getStripeClient(): Stripe {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    throw new Error("STRIPE_SECRET_KEY is not configured.");
  }

  return new Stripe(secretKey);
}

async function findCustomer(stripe: Stripe, userId: string): Promise<Stripe.Customer | null> {
  const queryUserId = userId.replace(/'/g, "\\'");
  const customers = await stripe.customers.search({
    query: `metadata['user_id']:'${queryUserId}'`,
    limit: 1,
  });
  return customers.data.at(0) ?? null;
}

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Authentification requise." }, { status: 401 });
  }

  try {
    const stripe = getStripeClient();
    const customer = await findCustomer(stripe, userId);
    if (!customer) {
      return NextResponse.json({
        plan: "free",
        status: "inactive",
        invoices: [],
      });
    }

    const [subscriptions, invoices] = await Promise.all([
      stripe.subscriptions.list({ customer: customer.id, status: "all", limit: 1 }),
      stripe.invoices.list({ customer: customer.id, limit: 8 }),
    ]);

    const subscription = subscriptions.data.at(0);
    const priceId = subscription?.items.data.at(0)?.price.id ?? "";
    const selected = priceId ? findPlanByPriceId(priceId) : null;

    return NextResponse.json({
      plan: selected?.plan.slug ?? "free",
      status: subscription?.status ?? "inactive",
      currentPeriodEnd: subscription?.current_period_end
        ? new Date(subscription.current_period_end * 1000).toISOString()
        : null,
      trialEnd: subscription?.trial_end
        ? new Date(subscription.trial_end * 1000).toISOString()
        : null,
      invoices: invoices.data.map((invoice) => ({
        id: invoice.id,
        amountPaid: invoice.amount_paid,
        currency: invoice.currency,
        hostedInvoiceUrl: invoice.hosted_invoice_url,
        invoicePdf: invoice.invoice_pdf,
        status: invoice.status,
        created: new Date(invoice.created * 1000).toISOString(),
      })),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erreur facturation inconnue.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
