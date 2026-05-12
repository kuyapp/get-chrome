type Channel = "stable" | "beta" | "dev";
type ChannelSelection = Channel | "all";

type Env = {
  GOOGLE_UPDATE_URL?: string;
  CACHE_TTL_SECONDS?: string;
  URL_TIMEOUT_SECONDS?: string;
};

type CachedUrls = {
  expiresAt: number;
  urls: string[];
};

const SUPPORTED_CHANNELS: Channel[] = ["stable", "beta", "dev"];
const ALL_CHANNELS = "all";
const DEFAULT_GOOGLE_UPDATE_URL = "https://tools.google.com/service/update2";
const DEFAULT_CACHE_TTL_SECONDS = 60;
const DEFAULT_URL_TIMEOUT_SECONDS = 20;
const HTML_HEADERS = { "Content-Type": "text/html; charset=utf-8" };

const PAYLOADS: Record<Channel, string> = {
  stable:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-stable-multi-chrome"><updatecheck/></app></request>',
  beta:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-beta-multi-chrome"><updatecheck/></app></request>',
  dev:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-dev-statsdef_1"><updatecheck/></app></request>',
};

const cache = new Map<Channel, CachedUrls>();

export default {
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const selection = channelSelectionForPath(url.pathname);

    if (!selection) {
      return Response.redirect(new URL("/channel/stable", url).toString(), 302);
    }

    try {
      const links = await installerUrlsFor(selection, env);
      return new Response(renderIndex(links), { headers: HTML_HEADERS });
    } catch (error) {
      return new Response(renderError(error), { status: 502, headers: HTML_HEADERS });
    }
  },
};

function channelSelectionForPath(pathname: string): ChannelSelection | null {
  if (pathname === "/" || pathname === "/channel/" || pathname === "/channel/stable") {
    return "stable";
  }

  if (pathname === "/channel/beta") {
    return "beta";
  }

  if (pathname === "/channel/dev") {
    return "dev";
  }

  if (pathname === "/channel/all") {
    return ALL_CHANNELS;
  }

  if (pathname.startsWith("/channel/")) {
    return null;
  }

  return null;
}

async function installerUrlsFor(selection: ChannelSelection, env: Env): Promise<Map<Channel, string[]>> {
  const selectedChannels = selection === ALL_CHANNELS ? SUPPORTED_CHANNELS : [selection];
  const links = new Map<Channel, string[]>();

  for (const channel of selectedChannels) {
    links.set(channel, await installerUrls(channel, env));
  }

  return links;
}

async function installerUrls(channel: Channel, env: Env): Promise<string[]> {
  const cachedUrls = cache.get(channel);
  const now = Date.now();
  if (cachedUrls && cachedUrls.expiresAt > now) {
    return [...cachedUrls.urls];
  }

  const xmlBody = await fetchGoogleUpdate(PAYLOADS[channel], env);
  const urls = parseInstallerUrls(xmlBody);
  cache.set(channel, {
    expiresAt: now + secondsFromEnv(env.CACHE_TTL_SECONDS, DEFAULT_CACHE_TTL_SECONDS) * 1000,
    urls,
  });
  return urls;
}

async function fetchGoogleUpdate(payload: string, env: Env): Promise<string> {
  const endpoint = env.GOOGLE_UPDATE_URL ?? DEFAULT_GOOGLE_UPDATE_URL;
  const timeoutSeconds = secondsFromEnv(env.URL_TIMEOUT_SECONDS, DEFAULT_URL_TIMEOUT_SECONDS);
  const abortController = new AbortController();
  const timeout = setTimeout(() => abortController.abort(), timeoutSeconds * 1000);

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "text/xml; charset=UTF-8" },
      body: payload,
      signal: abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`Google Update returned HTTP ${response.status}`);
    }

    return await response.text();
  } finally {
    clearTimeout(timeout);
  }
}

function parseInstallerUrls(xmlBody: string): string[] {
  const packageName = firstAttribute(xmlBody, /<package\b[^>]*\bname="([^"]+)"/);
  const codebases = [...xmlBody.matchAll(/<url\b[^>]*\bcodebase="([^"]+)"/g)].map((match) => match[1]);

  if (!packageName || codebases.length === 0) {
    const status = firstAttribute(xmlBody, /<updatecheck\b[^>]*\bstatus="([^"]+)"/) ?? "unknown";
    throw new Error(`Google Update response did not include installer URLs: ${status}`);
  }

  return codebases.map((codebase) => `${decodeXmlAttribute(codebase)}${decodeXmlAttribute(packageName)}`);
}

function firstAttribute(xmlBody: string, pattern: RegExp): string | null {
  return pattern.exec(xmlBody)?.[1] ?? null;
}

function secondsFromEnv(value: string | undefined, fallback: number): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function renderIndex(links: Map<Channel, string[]>): string {
  const sections = [...links]
    .map(
      ([channel, urls]) => `
          <h4>${escapeHtml(channel)}</h4>
${urls.map((link) => `          <pre><code>${escapeHtml(link)}</code></pre>`).join("\n")}`,
    )
    .join("\n");

  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Get Chrome Installer</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: #333; }
      .container { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
      .header, .footer { border-bottom: 1px solid #e5e5e5; margin-bottom: 24px; }
      .footer { border-bottom: 0; border-top: 1px solid #e5e5e5; margin-top: 24px; padding-top: 16px; color: #777; }
      .text-muted { color: #777; font-weight: 400; }
      pre { background: #f7f7f9; border: 1px solid #e1e1e8; border-radius: 4px; padding: 9px 14px; overflow-x: auto; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h3 class="text-muted">Get Chrome Installer</h3>
      </div>
      <main>
${sections}
      </main>
      <div class="footer">
        <p>kuyapp</p>
      </div>
    </div>
  </body>
</html>`;
}

function renderError(error: unknown): string {
  const message = error instanceof Error ? error.message : "Unknown error";
  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Get Chrome Installer Error</title>
  </head>
  <body>
    <main>
      <h1>Unable to load Chrome installer URLs</h1>
      <p>${escapeHtml(message)}</p>
    </main>
  </body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function decodeXmlAttribute(value: string): string {
  return value
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&amp;", "&");
}
