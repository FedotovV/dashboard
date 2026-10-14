---
name: astrowind
description: Build and change the AstroWind site in site/. Use when adding pages, widgets, styles, blog posts, the header, or deployment for that site.
---

# AstroWind

The site is `site/`, created from `arthelokyo/astrowind`. Guides live in `site/.agents/skills/`. Read the guide that matches the task and follow it. Paths inside those guides are relative to `site/`.

From `site/`:

```bash
npm install
npm run dev
```

The dev server is `http://127.0.0.1:4321`. Requests to `/api` are proxied to the dashboard at `http://127.0.0.1:8765`. The site does not compute dashboard metrics.

| Task | Guide |
| --- | --- |
| Page sections | `use-widgets.md` |
| New page | `add-page.md` |
| New component | `add-component.md` |
| Styles and tokens | `styling.md`, `use-shadcn-tokens.md` |
| Header | `customize-header.md` |
| Blog post | `add-blog-post.md` |
| Turn the blog off | `disable-blog.md` |
| Content that exists at build time | `content-at-build-time.md` |
| Landing page | `write-landing-page.md` |
| Open Graph image | `set-open-graph-image.md` |
| Structured data | `add-structured-data.md` |
| Contact form | `configure-contact-form.md` |
| Decap CMS | `setup-decap-cms.md` |
| Deploy on Cloudflare | `deploy-cloudflare.md` |
| Deploy under a base path | `deploy-with-base-path.md` |
