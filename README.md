# Avinash Holmes — personal website

The source for [avinasholmes.com](https://avinasholmes.com), hosted with GitHub Pages.

## Site map

- `index.html` — research-led homepage
- `about.html` — personal biography and professional profile links
- `research.html` — connected research themes and selected scientific presentations
- `publications.html` — verified peer-reviewed publications and public preprints
- `writing.html` — searchable Blogger feed and restored writing archive
- `photography.html` — photography collection
- `articles/` — 52 articles, stories, and poems recovered from the previous website
- `assets/images/` — web-optimized images used by the redesign

## Publishing new writing

Continue publishing on the existing Blogger account. The public Blogger feed is loaded automatically by the website, so no Blogger password or credential is stored in this repository.

`assets/blogger-posts.js` is a static fallback. To refresh it manually after downloading the public feed:

```sh
node scripts/import-blogger.mjs /path/to/blog-feed.json
```

## Restoring the archived website

The import script converts the saved GoDaddy article pages into lightweight native HTML pages:

```sh
node scripts/import-archive.mjs "/path/to/important"
```

## Adding photographs

Add web-sized JPEG files to `assets/images/`, then add the desired photograph to `photography.html`. Keep the long edge around 1600–2000 pixels so pages remain fast.
