const GOOGLE_UPDATE_URL = "https://tools.google.com/service/update2";
const XML_CONTENT_TYPE = "text/xml; charset=UTF-8";

export type Channel = "stable" | "beta" | "dev";
type ChannelSelection = Channel | "all";

const SUPPORTED_CHANNELS: readonly Channel[] = ["stable", "beta", "dev"];

const REQUEST_PAYLOADS: Record<Channel, string> = {
  stable:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-stable-multi-chrome"><updatecheck/></app></request>',
  beta:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-beta-multi-chrome"><updatecheck/></app></request>',
  dev:
    '<?xml version="1.0" encoding="UTF-8"?><request protocol="3.0" version="1.3.32.7" shell_version="1.3.32.7" ismachine="1" installsource="update3web-ondemand" dedup="cr"><hw physmemory="4" sse="1" sse2="1" sse3="1" ssse3="1" sse41="0" sse42="0" avx="0"/><os platform="win" version="10.0.14393.693" sp="" arch="x64"/><app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" version="" nextversion="" ap="x64-dev-statsdef_1"><updatecheck/></app></request>',
};

export class InstallerFetchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InstallerFetchError";
  }
}

/**
 * Fetches the Google Update response for a Chrome channel and returns full installer URLs.
 */
export async function fetchInstallerUrls(channel: Channel): Promise<string[]> {
  const body = REQUEST_PAYLOADS[channel];
  if (!body) {
    throw new InstallerFetchError(`Unsupported Chrome channel: ${channel}`);
  }

  let response: Response;
  try {
    response = await fetch(GOOGLE_UPDATE_URL, {
      method: "POST",
      headers: { "Content-Type": XML_CONTENT_TYPE },
      body,
    });
  } catch {
    throw new InstallerFetchError("Unable to fetch Chrome installer metadata");
  }

  if (!response.ok) {
    throw new InstallerFetchError(
      `Google Update returned HTTP ${response.status}`,
    );
  }

  const xml = await response.text();
  return parseInstallerUrls(xml);
}

// Cloudflare Workers do not provide DOMParser, so this uses constrained
// regular expressions for the small Google Update response shape we consume.
function parseInstallerUrls(xml: string): string[] {
  if (!looksLikeXml(xml)) {
    throw new InstallerFetchError("Google Update returned invalid XML");
  }

  const updateCheck = allElementBodies(xml, "app")
    .map((appBody) => firstElementBody(appBody, "updatecheck"))
    .find((body): body is string => body !== undefined);
  if (updateCheck === undefined) {
    throw missingMetadataError(xml);
  }

  const manifest = firstElementBody(updateCheck, "manifest");
  const packages = manifest ? firstElementBody(manifest, "packages") : undefined;
  const packageTag = packages ? firstStartTag(packages, "package") : undefined;
  const packageName = packageTag ? attributeValue(packageTag, "name") : undefined;
  if (!packageName) {
    throw missingMetadataError(xml);
  }

  const urls = firstElementBody(updateCheck, "urls");
  const codebases = urls
    ? allStartTags(urls, "url").map((tag) => attributeValue(tag, "codebase"))
    : [];
  const installerUrls = codebases
    .filter(
      (codebase): codebase is string =>
        codebase !== undefined && codebase.length > 0,
    )
    .map((codebase) => codebase + packageName);

  if (installerUrls.length === 0) {
    throw missingMetadataError(xml);
  }

  return installerUrls;
}

function looksLikeXml(xml: string): boolean {
  const trimmed = xml.trim();
  return (
    trimmed.startsWith("<") &&
    /<response(?:\s|>)/.test(trimmed) &&
    /<\/response>\s*$/.test(trimmed)
  );
}

function firstElementBody(xml: string, tagName: string): string | undefined {
  return allElementBodies(xml, tagName)[0];
}

function allElementBodies(xml: string, tagName: string): string[] {
  const pattern = new RegExp(
    `<${tagName}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${tagName}>`,
    "gi",
  );
  return Array.from(xml.matchAll(pattern), (match) => match[1]);
}

function firstStartTag(xml: string, tagName: string): string | undefined {
  return allStartTags(xml, tagName)[0];
}

function allStartTags(xml: string, tagName: string): string[] {
  const pattern = new RegExp(`<${tagName}(?:\\s[^>]*)?/?>`, "gi");
  return Array.from(xml.matchAll(pattern), (match) => match[0]);
}

function attributeValue(tag: string, attributeName: string): string | undefined {
  const pattern = new RegExp(`${attributeName}\\s*=\\s*(["'])(.*?)\\1`, "i");
  const value = pattern.exec(tag)?.[2];
  return value === undefined ? undefined : decodeXmlAttribute(value);
}

function decodeXmlAttribute(value: string): string {
  return value.replace(
    /&(#x?[0-9a-f]+|amp|lt|gt|quot|apos);/gi,
    (entity, body) => {
      switch (body.toLowerCase()) {
        case "amp":
          return "&";
        case "lt":
          return "<";
        case "gt":
          return ">";
        case "quot":
          return '"';
        case "apos":
          return "'";
        default:
          return decodeNumericEntity(body, entity);
      }
    },
  );
}

function decodeNumericEntity(body: string, entity: string): string {
  const codePoint = body.toLowerCase().startsWith("#x")
    ? Number.parseInt(body.slice(2), 16)
    : Number.parseInt(body.slice(1), 10);
  return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : entity;
}

function missingMetadataError(xml: string): InstallerFetchError {
  const updateCheckTag = firstStartTag(xml, "updatecheck");
  const status = updateCheckTag
    ? attributeValue(updateCheckTag, "status") ?? "unknown"
    : "unknown";
  return new InstallerFetchError(
    `Google Update response did not include installer URLs: ${status}`,
  );
}

function channelsFor(selection: string): readonly Channel[] {
  if (selection === "all") {
    return SUPPORTED_CHANNELS;
  }
  if (isChannel(selection)) {
    return [selection];
  }
  return ["stable"];
}

function isChannel(value: string): value is Channel {
  return SUPPORTED_CHANNELS.includes(value as Channel);
}

function renderIndex(links: Partial<Record<Channel, string[]>>): Response {
  const channelSections = Object.entries(links)
    .map(([channel, urls]) => {
      const renderedUrls = urls
        .map((url) => `<pre><code>${escapeHtml(url)}</code></pre>`)
        .join("");
      return `<h4>${escapeHtml(channel)}</h4>${renderedUrls}`;
    })
    .join("");

  return htmlResponse(`<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Get Chrome Installer</title>
  </head>
  <body>
    <main class="container">
      <h3>Get Chrome Installer</h3>
      ${channelSections}
    </main>
  </body>
</html>`);
}

function renderError(error: unknown): Response {
  const message =
    error instanceof Error
      ? error.message
      : "Unable to fetch Chrome installer metadata";
  return htmlResponse(`<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Get Chrome Installer - Error</title>
  </head>
  <body>
    <main class="container">
      <h3>Get Chrome Installer</h3>
      <h4>Unable to load Chrome installer URLs</h4>
      <p>${escapeHtml(message)}</p>
    </main>
  </body>
</html>`, 502);
}

function htmlResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=UTF-8" },
  });
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (char) => {
    switch (char) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case "'":
        return "&#39;";
      case '"':
        return "&quot;";
      default:
        return char;
    }
  });
}

export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const match = /^\/channel\/?([^/]*)\/?$/.exec(url.pathname);
    const selection: ChannelSelection | string =
      url.pathname === "/" ? "stable" : match?.[1] || "stable";

    try {
      const links: Partial<Record<Channel, string[]>> = {};
      for (const channel of channelsFor(selection)) {
        links[channel] = await fetchInstallerUrls(channel);
      }
      return renderIndex(links);
    } catch (error) {
      return renderError(error);
    }
  },
};
