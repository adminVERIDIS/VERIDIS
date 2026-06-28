import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import Stripe from "stripe";

type PortalBody = {
  returnUrl: string;
};

function getStripeClient(): Stripe {
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey) {
    throw new Error("STRIPE_SECRET_KEY is not configured.");
  }

  return new Stripe(secretKey);
}

function parsePortalBody(value: unknown): PortalBody | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const returnUrl = (value as Record<string, unknown>).returnUrl;
  return typeof returnUrl === "string" ? { returnUrl } : null;
}

function isSafeReturnUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.hostname === "localhost";
  } catch {
    return false;
  }
}

async function findCustomerId(stripe: Stripe, userId: string): Promise<string | null> {
  const queryUserId = userId.replace(/'/g, "\\'");
  const customers = await stripe.customers.search({
    query: `metadata['user_id']:'${queryUserId}'`,
    limit: 1,
  });
  return customers.data.at(0)?.id ?? null;
}

export async function POST(request: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Authentification requise." }, { status: 401 });
  }

  const body = parsePortalBody(await request.json().catch(() => null));
  if (!body || !isSafeReturnUrl(body.returnUrl)) {
    return NextResponse.json({ error: "returnUrl invalide." }, { status: 400 });
  }

  try {
    const stripe = getStripeClient();
    const customerId = await findCustomerId(stripe, userId);
    if (!customerId) {
      return NextResponse.json({ error: "Customer Stripe introuvable." }, { status: 404 });
    }

    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: body.returnUrl,
    });

    return NextResponse.json({ url: session.url });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Erreur Stripe inconnue.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
