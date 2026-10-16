# Express Movers website

Static site for Express Movers LLC, Wilmington, NC. Built by Zan Media Group.
No framework, no database, no logins. Python 3 builds plain HTML.

## Build

    python3 build.py preview                    # preview/  links end in .html, yellow notes shown
    python3 build.py production                 # dist/     clean URLs for GitHub Pages
    python3 build.py production --allow-notes   # dry run while notes are still open

The production build refuses to run while any "Jared to confirm" note is left in the copy.
All copy and settings live in build.py. Styles are in src/styles.css, the one script is
src/site.js, photos are in src/img and fonts are in src/fonts.

## Publish

Push to main. The workflow in .github/workflows/pages.yml builds dist/ and publishes it.
In the repo settings choose Pages > Source > GitHub Actions, then set the custom domain to
www.expressmoversilm.com and tick Enforce HTTPS.

DNS at the registrar:

    A      @     185.199.108.153
    A      @     185.199.109.153
    A      @     185.199.110.153
    A      @     185.199.111.153
    CNAME  www   <github-account>.github.io

## Before launch

1. Resolve every note on the launch checklist page (preview/launch-checklist.html).
2. Set form_action in the SITE block at the top of build.py. Add ga_id and pixel_id only
   after the privacy policy has a section about them.
3. Recount the ratings and the HireAHelper move count, and update them in build.py.
4. Bump "version" in build.py whenever styles.css or site.js changes.

## Photos

Photos in src/img are made from the full-size originals by tools/make_images.py, which
writes several widths of each one as WebP plus manifest.json. build.py reads the manifest
and writes the srcset for you:

    python3 tools/make_images.py "/path/to/Express Movers Photos"

In build.py a photo is placed with pic("name", "alt text", sizes). No stock photos: the
gallery says there are none.

## Checks run on October 8, 2026

- Lighthouse, phone profile: homepage 98 performance, 100 accessibility, 100 best
  practices, 100 SEO. Local moving 100 across the board. Gallery 95 performance.
- axe-core, WCAG 2.1 AA: no violations on any page at desktop or phone width.
- html-validate: no errors.
- Every internal link, anchor, photo and structured data block checked by script.

## Security

What the site does:

- Every production page carries a Content-Security-Policy that only runs this site's own
  script and stylesheet, and blocks frames, plugins and inline code. If form_action, ga_id
  or pixel_id is set, the build adds exactly the hosts they need and nothing else.
- Fonts are stored in the repo. With analytics off, a visit makes no request to any other site.
- No inline scripts and no inline styles, so the policy never needs 'unsafe-inline'.
- The form has a hidden spam trap, a minimum fill time and length limits. It posts with
  fetch, so a failed send always shows the phone number instead of losing the lead.
- Outside links open with rel="noopener noreferrer".
- /.well-known/security.txt gives a contact for reporting a problem.

What needs a person:

- Two-factor sign-in on GitHub, the registrar and the Google account that owns the profile.
- Verify the domain in GitHub (Settings > Pages > Add a domain) before pointing DNS here.
  If the Pages site is ever switched off, remove the DNS records the same day.
- Registrar lock and auto-renew on the domain.
- Protect the main branch so every change goes through a pull request.
- Never commit a password, API key or private token. This repo and its output are public.
  A form address or an analytics ID is fine.

Known limit: GitHub Pages cannot send HTTP headers, so the policy is a meta tag. It cannot
set frame-ancestors or HSTS. Putting Cloudflare in front of the site would add both.

## Old addresses

The production build writes forwarding pages for 26 addresses from the previous site: the
12 /service-areas/ city pages, /long-distance-moving, /blog, the 10 blog posts, and the
two removal pages. Edit the REDIRECTS dict in build.py to change where they point.
