import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, join } from "node:path";

const archiveRoot = process.argv[2];
if (!archiveRoot) {
  console.error("Usage: node scripts/import-archive.mjs ARCHIVE_FOLDER");
  process.exit(1);
}
const outputRoot = new URL("../", import.meta.url).pathname;
const articleRoot = join(outputRoot, "articles");

mkdirSync(articleRoot, { recursive: true });

const groups = [
  { directory: "Science and health", category: "Science & Health", skip: "Science and Health_main page.html" },
  { directory: "SciFi and Poems", category: "Stories & Poems", skip: "SciFi and POEMS .html" },
];

const decode = (value = "") => value
  .replace(/&nbsp;/gi, " ")
  .replace(/&mdash;/gi, "—")
  .replace(/&ndash;/gi, "–")
  .replace(/&rsquo;/gi, "’")
  .replace(/&lsquo;/gi, "‘")
  .replace(/&ldquo;/gi, "“")
  .replace(/&rdquo;/gi, "”")
  .replace(/&amp;/gi, "&")
  .replace(/&#39;/g, "'")
  .replace(/&quot;/gi, '"')
  .replace(/<[^>]+>/g, " ")
  .replace(/\s+/g, " ")
  .trim();

const escapeHtml = (value = "") => value.replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

const slugify = (value, index) => {
  const slug = value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 72);
  return slug || `archive-${String(index + 1).padStart(2, "0")}`;
};

const xpath = (file, expression) => {
  try {
    return execFileSync("xmllint", ["--html", "--recover", "--xpath", expression, file], {
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
};

const sanitizeArticle = (html) => html
  .replace(/<(script|style|svg|iframe|form)\b[\s\S]*?<\/\1>/gi, "")
  .replace(/<img\b[^>]*>/gi, "")
  .replace(/<!--([\s\S]*?)-->/g, "")
  .replace(/\s(?:class|style|data-[\w:-]+|id|role|aria-[\w-]+|rel|target)="[^"]*"/gi, "")
  .replace(/<span\b[^>]*>/gi, "")
  .replace(/<\/span>/gi, "")
  .replace(/<div\b[^>]*>/gi, "")
  .replace(/<\/div>/gi, "")
  .replace(/<(p|h2|h3|h4|ul|ol|li|blockquote)\b[^>]*>/gi, "<$1>")
  .replace(/<br\s*\/?>\s*<br\s*\/?>/gi, "</p><p>")
  .replace(/<p>\s*<\/p>/gi, "")
  .replace(/\s{2,}/g, " ")
  .trim();

const shell = (title, description, category, date, content) => `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)} | Avinash Holmes</title>
  <meta name="description" content="${escapeHtml(description)}">
  <link rel="stylesheet" href="../assets/styles.css">
</head>
<body class="article-page">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header compact">
    <a class="brand" href="../index.html"><span class="brand-mark">AH</span><span>Avinash Holmes</span></a>
    <nav class="desktop-nav" aria-label="Primary navigation">
      <a href="../index.html">Home</a><a href="../index.html#research">Research</a><a href="../writing.html">Writing</a><a href="../photography.html">Photography</a><a href="../index.html#about">About</a>
    </nav>
  </header>
  <main id="main" class="article-shell">
    <a class="back-link" href="../writing.html">← Writing archive</a>
    <article>
      <div class="article-kicker"><span>${escapeHtml(category)}</span>${date ? `<span>${escapeHtml(date)}</span>` : ""}</div>
      <h1>${escapeHtml(title)}</h1>
      <p class="article-deck">Recovered from the original Avinash Holmes website archive.</p>
      <div class="article-body">${content}</div>
    </article>
  </main>
  <footer class="site-footer"><p>© 2026 Avinash Holmes</p><a href="../writing.html">More writing</a></footer>
</body>
</html>`;

const posts = [];
const usedSlugs = new Set();

for (const group of groups) {
  const directory = join(archiveRoot, group.directory);
  const files = readdirSync(directory).filter((file) => file.endsWith(".html") && file !== group.skip);
  for (const file of files) {
    const fullPath = join(directory, file);
    const raw = readFileSync(fullPath, "utf8");
    const titleMatch = raw.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    const title = decode(titleMatch?.[1] || basename(file, ".html"));
    const index = posts.length;
    let slug = slugify(title, index);
    if (usedSlugs.has(slug)) slug = `${slug}-${index + 1}`;
    usedSlugs.add(slug);

    const date = decode(xpath(fullPath, 'string(//*[@data-aid="RSS_POST_DATE"])'));
    const originalCategory = decode(xpath(fullPath, 'string(//*[@data-aid="RSS_POST_CATEGORIES"])'));
    const sourceContent = xpath(fullPath, '//div[@data-ux="BlogContent"]');
    const content = sanitizeArticle(sourceContent) || `<p>${decode(xpath(fullPath, 'string(//body)'))}</p>`;
    const plain = decode(content);
    const excerpt = plain.slice(0, 210).replace(/\s+\S*$/, "") + (plain.length > 210 ? "…" : "");
    const category = originalCategory || group.category;

    writeFileSync(join(articleRoot, `${slug}.html`), shell(title, excerpt, category, date, content));
    posts.push({ title, date, category, group: group.category, excerpt, url: `articles/${slug}.html` });
  }
}

posts.sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: "base" }));
writeFileSync(join(outputRoot, "assets", "archive-posts.js"), `window.ARCHIVE_POSTS = ${JSON.stringify(posts, null, 2)};\n`);
console.log(`Imported ${posts.length} archived articles.`);
