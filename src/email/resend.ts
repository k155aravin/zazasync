import type { Env } from "../types/env";
import { getQueuedAlerts, markAlert } from "../db/repository";

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildEmailHtml(env: Env, alert: { product_name: string; slug: string; store_name: string | null; store_code: string | null }): string {
  const productUrl = `${env.PUBLIC_SITE_ORIGIN.replace(/\/$/, "")}/products/${encodeURIComponent(alert.slug)}`;
  const storeLine = alert.store_name ? `<p><strong>Store:</strong> ${escapeHtml(alert.store_name)}</p>` : "";
  return `<!doctype html>
<html lang="en">
  <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #1f2933;">
    <h1 style="font-size: 20px;">ZazaSync restock alert</h1>
    <p>The product you are watching appears available in the latest public SQDC snapshot.</p>
    <p><strong>Product:</strong> ${escapeHtml(alert.product_name)}</p>
    ${storeLine}
    <p><a href="${productUrl}" style="color: #2563eb;">View product on ZazaSync</a></p>
    <p style="font-size: 12px; color: #6b7280;">Availability can change quickly. ZazaSync shows cached public snapshot evidence and does not sell cannabis.</p>
  </body>
</html>`;
}

export async function sendQueuedEmailAlerts(env: Env): Promise<{ attempted: number; sent: number; failed: number; skipped: number }> {
  const alertsEnabled = (env.ALERTS_ENABLED || "false").toLowerCase() === "true";
  const queued = await getQueuedAlerts(env, 50);
  let attempted = 0;
  let sent = 0;
  let failed = 0;
  let skipped = 0;

  for (const alert of queued.results ?? []) {
    attempted += 1;
    if (!alertsEnabled || !env.RESEND_API_KEY) {
      await markAlert(env, alert.id, "skipped", null, "Alerts are disabled or RESEND_API_KEY is not configured.");
      skipped += 1;
      continue;
    }

    const payload = {
      from: `${env.ALERT_FROM_NAME || "ZazaSync Alerts"} <${env.ALERT_FROM_EMAIL || "alerts@zazasync.com"}>`,
      to: [alert.recipient],
      subject: `ZazaSync: ${alert.product_name} may be back in stock`,
      html: buildEmailHtml(env, alert)
    };

    try {
      const response = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          "authorization": `Bearer ${env.RESEND_API_KEY}`,
          "content-type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const text = await response.text();
      if (!response.ok) throw new Error(`Resend ${response.status}: ${text.slice(0, 500)}`);
      let id: string | null = null;
      try {
        id = JSON.parse(text).id || null;
      } catch {
        id = null;
      }
      await markAlert(env, alert.id, "sent", id, null);
      sent += 1;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await markAlert(env, alert.id, "failed", null, message.slice(0, 1000));
      failed += 1;
    }
  }

  return { attempted, sent, failed, skipped };
}
