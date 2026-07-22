/**
 * kk-dashboard Cloudflare Worker
 * Cron Triggers: 6x daily at Beijing 0/9/11/15/19/22 (UTC 16/1/3/7/11/14)
 * Triggers GitHub Actions workflow_dispatch on each scheduled run
 */

export default {
  async scheduled(event, env, ctx) {
    const repo = "JNC121314/kk-dashboard";
    const workflow = "daily-update.yml";
    const timestamp = new Date().toISOString();

    try {
      const response = await fetch(
        `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.GH_TOKEN}`,
            Accept: "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "kk-dashboard-cron-worker",
          },
          body: JSON.stringify({ ref: "main" }),
        }
      );

      if (response.status === 204) {
        console.log(`[${timestamp}] OK: workflow triggered`);
      } else {
        const text = await response.text();
        console.log(`[${timestamp}] FAIL: ${response.status} ${text}`);
      }
    } catch (error) {
      console.log(`[${timestamp}] ERROR: ${error.message}`);
    }
  },

  async fetch(request, env) {
    return new Response(
      JSON.stringify({
        service: "kk-dashboard-cron-trigger",
        status: "active",
        timestamp: new Date().toISOString(),
        schedule: "6x daily (Beijing 0/9/11/15/19/22 = UTC 16/1/3/7/11/14)",
        repo: "JNC121314/kk-dashboard",
        workflow: "daily-update.yml",
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  },
};
