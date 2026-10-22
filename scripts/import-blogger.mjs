import { readFileSync, writeFileSync } from "node:fs";

const input = process.argv[2] || "/private/tmp/avinash-site-source/blog-feed.json";
const output = new URL("../assets/blogger-posts.js", import.meta.url);
const feed = JSON.parse(readFileSync(input, "utf8")).feed;

const strip = (html = "") => html
  .replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, "")
  .replace(/<[^>]+>/g, " ")
  .replace(/&nbsp;/gi, " ")
  .replace(/&amp;/gi, "&")
  .replace(/&#39;/g, "'")
  .replace(/&quot;/gi, '"')
  .replace(/\s+/g, " ")
  .trim();

const posts = (feed.entry || []).map((entry) => {
  const alternate = entry.link?.find((link) => link.rel === "alternate")?.href;
  const image = entry["media$thumbnail"]?.url?.replace(/s72-/, "s640-") || "";
  const excerpt = strip(entry.content?.$t || "").slice(0, 220).replace(/\s+\S*$/, "") + "…";
  return {
    title: entry.title?.$t?.trim(),
    date: entry.published?.$t,
    categories: (entry.category || []).map((item) => item.term),
    url: alternate,
    image,
    excerpt,
  };
});

writeFileSync(output, `window.BLOGGER_POSTS = ${JSON.stringify(posts, null, 2)};\n`);
console.log(`Imported ${posts.length} Blogger posts.`);
