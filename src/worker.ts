import type { Env } from "./types/env";
import { runSqdcCrawl } from "./crawler/sqdc";
import { sendQueuedEmailAlerts } from "./email/resend";
import { handleRequest } from "./http/router";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return handleRequest(request, env);
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil((async () => {
      const crawl = await runSqdcCrawl(env, false);
      if (crawl.crawlId !== 0) {
        await sendQueuedEmailAlerts(env);
      }
    })());
  }
};
