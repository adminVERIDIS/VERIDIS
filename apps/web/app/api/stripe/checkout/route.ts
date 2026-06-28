import { auth, currentUser } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import Stripe from "stripe";

import { findPlanByPriceId } from "../../../../lib/billing/pricing";

type CheckoutBody = {
  priceId: string;
  successUrl: string;
  cancelUrl: string;
};

function getStripeClient(): Stripe {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    throw new Error("STRIPE_SECRET_KEY is not configured.");
  }

  return new Stripe(secretKey);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseCheckoutBody(value: unknown): CheckoutBody | null {
  if (!isRecord(value)) return null;
  const { priceId, successUrl, cancelUrl } = value;
  if (typeof priceId !== "string") return null;
  if (typeof successUrl !== "string") return null;
  if (typeof cancelUrl !== "string") return null;
  return { priceId, successUrl, cancelUrl };
}

function isSafeUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.hostname === "localhost";
  } catch {
    return false;
  }
}

async function getOrCreateCustomer(stripe: Stripe, userId: string, email?: string) {
  const queryUserId = userId.replace(/'/g, "\\'");
  const existing = await stripe.customers.search({
    query: `metadata['user_id']:'${queryUserId}'`,
    limit: 1,
  });

  const customer = existing.data.at(0);
  if (customer) return customer;

  return stripe.customers.create({
    email,
    metadata: { user_id: userId },
  });
}

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Authentification requise." }, { status: 401 });
  }

  const body = parseCheckoutBody(await request.json().catch(() => null));
  if (!body) {
    return NextResponse.json({ error: "Payload checkout invalide." }, { status: 400 });
  }

  const selected = findPlanByPriceId(body.priceId);
  if (!selected) {
    return NextResponse.json({ error: "priceId Stripe invalide." }, { status: 400 });
  }

  if (!isSafeUrl(body.successUrl) || !isSafeUrl(body.cancelUrl)) {
    return NextResponse.json({ error: "URL de retour invalide." }, { status: 400 });
  }

  try {
    const stripe = getStripeClient();
    const user = await currentUser();
    const email = user?.primaryEmailAddress?.emailAddress;
    const customer = await getOrCreateCustomer(stripe, userId, email);

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: customer.id,
      success_url: body.successUrl,
      cancel_url: body.cancelUrl,
      line_items: [{ price: body.priceId, quantity: 1 }],
      payment_method_collection: "always",
      allow_promotion_codes: true,
      automatic_tax: { enabled: true },
      client_reference_id: userId,
      metadata: {
        user_id: userId,
        plan: selected.plan.slug,
        interval: selected.interval,
        price_id: body.priceId,
      },
      subscription_data: {
        trial_period_days: 14,
        metadata: {
          user_id: userId,
          plan: selected.plan.slug,
          interval: selected.interval,
          price_id: body.priceId,
        },
      },
    });

    return NextResponse.json({ sessionId: session.id, url: session.url });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erreur Stripe inconnue.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
