#!/usr/bin/env python3
"""Express Movers site builder. No dependencies beyond Python 3.

  python3 build.py preview      -> preview/   links end in .html, yellow notes shown, noindex
  python3 build.py production   -> dist/      clean URLs for GitHub Pages, security policy on,
                                              refuses to build while a "Jared to confirm" note is left
  python3 build.py production --allow-notes   build anyway, for a dry run

All copy and settings live in this file. Styles: src/styles.css. Script: src/site.js.
Photos: src/img. Fonts: src/fonts. Nothing is loaded from another website unless an
analytics ID is set below.
"""
import base64, html, json, os, re, shutil, sys
from urllib.parse import urlparse

MODE = sys.argv[1] if len(sys.argv) > 1 else "preview"
ALLOW_NOTES = "--allow-notes" in sys.argv
PREVIEW = MODE == "preview"
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "preview" if PREVIEW else "dist")

SITE = {
    "domain": "https://www.expressmoversilm.com",
    "host": "www.expressmoversilm.com",
    "name": "Express Movers",
    "legal": "Express Movers LLC",
    "phone": "(704) 999-3714",
    "tel": "tel:+17049993714",
    "tel_schema": "+1-704-999-3714",
    "email": "expressmovers.go@gmail.com",
    "hours": "Open every day, 8am to 7pm",
    "google": "https://www.google.com/maps/place/Express+Movers+LLC/@34.2242571,-77.8183104,116413m/data=!3m2!1e3!4b1!4m6!3m5!1s0xa078297968b54fb9:0x7f36421c5c49b2aa!8m2!3d34.2242571!4d-77.8183104!16s%2Fg%2F11vw_rk8r2",
    "hireahelper": "https://www.hireahelper.com/movers/wilmington_nc/express-movers-wilmington-1/",
    "uhaul": "https://movinghelp.com/express-movers",
    "facebook": "https://facebook.com/profile.php?id=61559322054676",
    "youtube": "https://youtube.com/@ExpressMoversLLC",
    "pinterest": "https://pinterest.com/ExpressMovers77/",
    "counted": "October 2026",
    "updated": "October 8, 2026",
    "version": "20261008i",         # bump when styles.css or site.js changes, so browsers refetch
    # ---- Fill these in before launch. Never put a password, API key or private token here:
    # ---- this file and everything it builds are public.
    "form_action": "",              # e.g. https://formspree.io/f/xxxxxxxx  (empty = form switched off)
    "ga_id": "",                    # Google Analytics ID made for Express Movers, e.g. G-XXXXXXX
    "pixel_id": "",                 # Meta Pixel made for Express Movers. Do not reuse another business's pixel.
    "security_contact": "zane@zanmediagroup.com",
}

NAV = [("moving-help", "Moving help"), ("local-moving", "Local moving"), ("heavy-items", "Heavy items"),
       ("service-area", "Service area"), ("reviews", "Reviews"), ("about", "About")]

# Old addresses from the previous site, sent to the closest page that still exists.
REDIRECTS = {
    "long-distance-moving": "service-area",
    "appliance-removal": "index",
    "furniture-removal": "index",
    "blog": "index",
    "how-to-vet-a-wilmington-mover-before-you-book": "faq",
    "long-distance-moving-in-wilmington-nc-planning-your-interstate-relocation": "service-area",
    "storage-services-in-charlotte-nc-flexible-solutions-during-your-move": "moving-help",
    "specialty-item-moving-in-raleigh-nc-custom-handling-for-valuables": "heavy-items",
    "appliance-removal-in-durham-nc-responsible-recycling-and-disposal": "index",
    "commercial-moving-in-fayetteville-nc-coordinating-office-relocations": "local-moving",
    "furniture-assembly-in-greensboro-nc-efficient-setup-after-your-move": "local-moving",
    "packing-services-in-durham-nc-protect-your-belongings-during-transport": "faq",
    "appliance-removal-in-fayetteville-nc-efficient-disposal-and-recycling": "index",
    "furniture-removal-in-greensboro-nc-safe-handling-and-proper-disposal": "index",
}
for _city in ["wilmington-nc", "charlotte-nc", "raleigh-nc", "greensboro-nc", "fayetteville-nc", "durham-nc",
              "asheville-nc", "winston-salem-nc", "hickory-nc", "gastonia-nc", "concord-nc", "high-point-nc"]:
    REDIRECTS["service-areas/" + _city] = "service-area"

NOTES = []  # (page slug, note text), collected while building


# ------------------------------------------------------------------ helpers
def url(slug, query=""):
    """Address of a page. Preview uses file names, production uses clean absolute paths."""
    anchor = ""
    if "#" in slug:
        slug, anchor = slug.split("#", 1)
        anchor = "#" + anchor
    if PREVIEW:
        return ("index.html" if slug == "index" else slug + ".html") + anchor
    return ("/" if slug == "index" else "/" + slug) + (("?" + query) if query else "") + anchor


def asset(path, versioned=False):
    v = ("?v=" + SITE["version"]) if versioned else ""
    return (path if PREVIEW else "/" + path) + v


MAN = json.load(open(os.path.join(SRC, "img", "manifest.json")))


def pic(name, alt, sizes, eager=False):
    """A responsive photo. Sizes and file names come from src/img/manifest.json."""
    m = MAN[name]
    ws = m["widths"]
    src = asset("img/%s-%d.webp" % (name, 400 if 400 in ws else ws[min(1, len(ws) - 1)]))
    srcset = ", ".join("%s %dw" % (asset("img/%s-%d.webp" % (name, w)), w) for w in ws)
    load = (' fetchpriority="high"' if name == "crew-tailgate" else "") if eager else ' loading="lazy" decoding="async"'
    return '<img src="%s" srcset="%s" sizes="%s" alt="%s" width="%d" height="%d"%s>' % (
        src, srcset, sizes, html.escape(alt, quote=True), m["w"], m["h"], load)


def canonical(slug):
    return SITE["domain"] + ("/" if slug == "index" else "/" + slug)


def ext(href, label):
    return '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (html.escape(href, quote=True), label)


def render(text, slug):
    """Swap the [[...]] tokens used in the page copy below."""
    def note(m):
        NOTES.append((slug, m.group(1)))
        return '<span class="tbc">Jared to confirm: %s</span>' % m.group(1)
    text = re.sub(r"\[\[tbc:(.*?)\]\]", note, text, flags=re.S)
    text = re.sub(r"\[\[preview:(.*?)\]\]",
                  (lambda m: '<p><span class="preview-note">%s</span></p>' % m.group(1)) if PREVIEW else "", text, flags=re.S)
    text = re.sub(r"\[\[url:([^\]|]+)(?:\|([^\]]*))?\]\]", lambda m: url(m.group(1), m.group(2) or ""), text)
    text = re.sub(r"\[\[img:([^\]]+)\]\]", lambda m: asset("img/" + m.group(1)), text)
    for key in ("phone", "tel", "email", "hours", "counted", "updated", "legal", "google", "hireahelper", "uhaul"):
        text = text.replace("[[%s]]" % key, SITE[key])
    left = re.findall(r"\[\[[^\]]*\]\]", text)
    if left:
        sys.exit("Unknown token on page %s: %s" % (slug, left[:3]))
    return text


def faq_block(items):
    rows = "".join('<details><summary>%s</summary><div class="answer">%s</div></details>\n' % (q, a) for q, a in items)
    return '<div class="faq">\n%s</div>' % rows


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def cta(title="Get a free estimate", text="Tell us what needs moving and when. We reply the same day during business hours."):
    return """<section class="section cta"><div class="wrap stack">
  <h2>%s</h2>
  <p>%s</p>
  <div class="actions"><a class="btn btn--light" href="[[url:contact]]">Send the details</a><a class="tel" href="[[tel]]">[[phone]]</a></div>
  <p class="small">[[hours]].</p>
</div></section>""" % (title, text)


def page_head(crumb, h1, lead, parent=None):
    up = ('<a href="[[url:%s]]">%s</a> / ' % parent) if parent else ""
    return """<section class="page-head"><div class="wrap">
  <p class="crumbs"><a href="[[url:index]]">Home</a> / %s%s</p>
  <h1>%s</h1>
  <p class="lead">%s</p>
</div></section>""" % (up, crumb, h1, lead)


PROOF = """<section class="proof" aria-label="Customer ratings"><div class="wrap">
  <ul>
    <li><b>4.9</b><span>stars on %s, 53 reviews</span></li>
    <li><b>685</b><span>customer reviews across three review sites</span></li>
    <li><b>700+</b><span>moves since October 2021</span></li>
    <li><b>15+</b><span>UNC Wilmington students on the crew</span></li>
  </ul>
  <p class="small proof-note">Counted [[counted]].</p>
</div></section>""" % ext("[[google]]", "Google")
LOGO = '<img src="%s" alt="Express Movers" width="200" height="107"%%s>' % asset("img/logo-200.webp")


# Real Google reviews, quoted word for word. First name only. Add or swap them here.
REVIEWS = [
    ("Josiah", "2026", "Could not say good enough things about this company from start to finish the owner Jared had great communication from the start and gave me a very fair price the unloading process was amazing they put everything where I wanted it to go highly recommend for anyone!"),
    ("Ryan", "2024", "Had them do two move jobs for me, very easy to work with. Great communication and moved my items with care. have recommended and would recommend!"),
    ("Davis", "2024", "Great company. Jared and his team are a couple of stand up guys. Moved an extra few pieces for me for free, really appreciate it guys. I will be a repeat customer!"),
]


def quotes_block():
    out = []
    for i, (name, year, text) in enumerate(REVIEWS):
        out.append('<figure class="quote%s"><blockquote><p>“%s”</p></blockquote>'
                   '<figcaption><b>%s</b>, 5 stars on Google, %s</figcaption></figure>'
                   % (" quote--lead" if i == 0 else "", html.escape(text, quote=False), name, year))
    return '<div class="quotes">\n%s\n</div>' % "\n".join(out)


def faq_ld(items):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a).replace("[[phone]]", SITE["phone"])}}
                           for q, a in items]}


def service_ld(slug, name, kind, desc):
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "serviceType": kind,
            "description": desc, "url": canonical(slug),
            "provider": {"@id": SITE["domain"] + "/#business"},
            "areaServed": {"@type": "City", "name": "Wilmington, NC"}}


# Photo sizes hints, by where the photo sits in the layout.
S_STRIP = "(max-width: 900px) 50vw, 280px"
S_SIDE = "(max-width: 900px) 100vw, 410px"
S_THUMB = "150px"

# ------------------------------------------------------------------ page copy
PAGES = []


def page(slug, title, desc, body, crumb=None, index=True, extra_ld=None, lead=False, in_sitemap=True, parent=None):
    PAGES.append(dict(slug=slug, title=title, desc=desc, body=body, crumb=crumb, index=index,
                      extra_ld=extra_ld or [], lead=lead, in_sitemap=in_sitemap, parent=parent))


# ---- home
HOME_FAQ = [
    ("Who does the moving?", "<p>Students from UNC Wilmington, each one trained by founder Jared Mazzola. The same crew handles your job from start to finish.</p>"),
    ("How do I get a price?", '<p>Call [[phone]] or send the <a href="[[url:contact]]">estimate form</a>. We ask about both addresses, the number of bedrooms, stairs and any heavy items, then give you a free estimate. We reply the same day during business hours.</p>'),
    ("Do I need to rent the truck?", '<p>For loading and unloading help, most customers book their own truck or container and we load and unload it. Not sure what to book? See the <a href="[[url:moving-help#truck]]">truck size guide</a> or call and we will help you work it out.</p>'),
    ("Is there a minimum?", "<p>Yes. The minimum booking is two movers for two hours. The estimate is free and there is no deposit to book.</p>"),
    ("Can you come today?", "<p>Yes, we take same-day jobs. Call [[phone]] and we will tell you when a crew can get to you.</p>"),
]

page("index",
     "Movers in Wilmington, NC | Local Moves & Moving Help",
     "Wilmington, NC movers for local moves and hourly loading and unloading help. Rated 4.9 stars on Google. Free estimates and same-day jobs: (704) 999-3714.",
     """<section class="hero"><div class="wrap hero-grid">
  <div class="hero-copy">
    <h1>Movers in Wilmington, NC</h1>
    <p class="lead">A local moving company with a crew of UNC Wilmington students. We load, unload and move apartments, houses and offices across the Cape Fear area. Since October 2021, and rated 4.9 stars on Google.</p>
    <div class="actions">
      <a class="btn" href="[[url:contact]]">Get a free estimate</a>
      <a class="tel" href="[[tel]]">[[phone]]</a>
    </div>
    <p class="small">[[hours]]. We take same-day jobs. No deposit to book.</p>
  </div>
  <figure class="hero-photo">
    """ + pic("crew-tailgate", "Five Express Movers crew members giving a thumbs up on the tailgate of a loaded moving truck", "(max-width: 900px) 100vw, 600px", eager=True) + """
  </figure>
</div></section>
""" + PROOF + """
<section class="section"><div class="wrap stack-lg">
  <h2>Moving services in Wilmington</h2>
  <div class="svc-list">
    <div class="svc">
      """ + pic("hand-truck-load", "A mover with a hand truck inside a loaded moving truck", S_THUMB) + """
      <div>
        <h3><a href="[[url:moving-help]]">Moving help: loading and unloading</a></h3>
        <p>Hourly moving labor for the truck, trailer, portable container or storage unit you rent. We load it tight so nothing shifts on the road, unload it at the other end, or both. Only need one end done? Book just the load or just the unload.</p>
      </div>
      <a class="go" href="[[url:moving-help]]">How moving help works</a>
    </div>
    <div class="svc">
      """ + pic("crew-ramp", "Three crew members standing at the ramp of a packed moving truck", S_THUMB) + """
      <div>
        <h3><a href="[[url:local-moving]]">Local moving</a></h3>
        <p>Apartment, house and office moves around Wilmington, done in one trip by one crew. We take the furniture apart and put it back together at the new place.</p>
      </div>
      <a class="go" href="[[url:local-moving]]">About local moves</a>
    </div>
    <div class="svc">
      """ + pic("pool-table", "Four crew members lifting a pool table with moving straps", S_THUMB) + """
      <div>
        <h3><a href="[[url:heavy-items]]">Piano, gun safe, hot tub and pool table moving</a></h3>
        <p>The things two people and a dolly cannot handle. We bring extra hands and move them for an added fee, on their own or as part of a move.</p>
      </div>
      <a class="go" href="[[url:heavy-items]]">Heavy items we move</a>
    </div>
  </div>
</div></section>

<section class="section section--band"><div class="wrap stack-lg">
  <h2>What Wilmington customers say</h2>
""" + quotes_block() + """
  <p>These are three of our 53 Google reviews, copied word for word. """ + ext("[[google]]", "Read the rest on Google") + """, or see <a href="[[url:reviews]]">more Express Movers reviews</a>.</p>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>How to get a moving estimate</h2>
  <ol class="route">
    <li><b>Call or send the form</b><span>Reach us at [[phone]] or fill in the estimate form. It takes about two minutes.</span></li>
    <li><b>Answer a few questions</b><span>Both addresses, how many bedrooms, any stairs, and anything heavy or awkward.</span></li>
    <li><b>Get your price</b><span>We reply the same day during business hours. The estimate is free and there is no deposit to book.</span></li>
    <li><b>We show up and lift</b><span>The crew arrives on the day you picked and does the heavy work.</span></li>
  </ol>
  <div class="actions"><a class="btn" href="[[url:contact]]">Start my estimate</a></div>
</div></section>

<section class="section section--band"><div class="wrap cols">
  <div class="stack-lg">
    <div class="stack">
      <h2>Why hire a UNCW moving crew</h2>
      <p>Jared Mazzola started Express Movers in October 2021 to help pay for school at UNCW. It grew into his career, and today he trains and manages a crew of more than 15 UNC Wilmington students. We are young, we are local, and we do this between classes because we are good at it.</p>
    </div>
    <dl class="facts">
      <div><dt>Started</dt><dd>October 2021</dd></div>
      <div><dt>Crew</dt><dd>More than 15 UNC Wilmington students</dd></div>
      <div><dt>Track record</dt><dd>More than 700 moves since October 2021</dd></div>
      <div><dt>Hours</dt><dd>Every day, 8am to 7pm</dd></div>
      <div><dt>Estimates</dt><dd>Free, with no deposit to book</dd></div>
    </dl>
    <div class="actions"><a class="btn btn--quiet" href="[[url:about]]">Meet the crew</a></div>
  </div>
  <div class="mosaic">
    """ + pic("uncw-boxes", "A mover in a UNCW shirt giving two thumbs up in front of boxes stacked to the ceiling of a truck", "(max-width: 900px) 62vw, 370px") + """
    """ + pic("two-movers-boxes", "Two movers standing in front of boxes stacked floor to ceiling in a truck", "(max-width: 900px) 32vw, 185px") + """
    """ + pic("ramp-uncw", "Two movers on a truck ramp, one wearing a UNCW shirt", "(max-width: 900px) 32vw, 185px") + """
  </div>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>What you can count on</h2>
  <div class="assure">
    <div><h3>One crew, start to finish</h3><p>The crew that loads you is the crew that unloads you. Local moves around Wilmington are done in one trip on the same day.</p></div>
    <div><h3>We bring the equipment</h3><p>Hand trucks, dollies with straps and the tools to take furniture apart come with every job at no extra charge. Have moving blankets on hand and we wrap your furniture in them.</p></div>
    <div><h3>Clear pricing, no deposit</h3><p>The smallest job is two movers for two hours. We charge by the hour for the crew, and we quote your job before you book. The estimate is free and there is no deposit. When you book direct you can pay by cash, Venmo, or invoice.</p></div>
    <div><h3>Same-day replies and same-day jobs</h3><p>Send a request between 8am and 7pm and we reply the same day. Need a crew today? Call [[phone]]. We take same-day jobs.</p></div>
  </div>
</div></section>

<section class="section section--band"><div class="wrap cols">
  <div class="stack">
    <h2>Movers for Wilmington and nearby towns</h2>
    <p>We are based in Wilmington and travel up to about an hour and ten minutes in any direction: Leland, the beaches, Hampstead, Southport, Burgaw, Jacksonville and Whiteville. Jobs outside Wilmington may carry a travel fee.</p>
    <div class="actions"><a class="btn btn--quiet" href="[[url:service-area]]">See every town we serve</a></div>
  </div>
  <dl class="facts">
    <div><dt>New Hanover</dt><dd>Wilmington, <a href="[[url:movers-carolina-beach-nc]]">Carolina Beach</a>, Kure Beach, <a href="[[url:movers-wrightsville-beach-nc]]">Wrightsville Beach</a>, Castle Hayne</dd></div>
    <div><dt>Brunswick</dt><dd><a href="[[url:movers-leland-nc]]">Leland</a>, Southport, Oak Island, Boiling Spring Lakes</dd></div>
    <div><dt>Pender</dt><dd><a href="[[url:movers-hampstead-nc]]">Hampstead</a>, Surf City, Topsail, Burgaw, Rocky Point</dd></div>
    <div><dt>Onslow</dt><dd>Jacksonville, Holly Ridge</dd></div>
    <div><dt>Columbus</dt><dd>Whiteville, Lake Waccamaw</dd></div>
  </dl>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>Questions about hiring movers</h2>
""" + faq_block(HOME_FAQ) + """
  <p><a href="[[url:faq]]">Read all moving questions</a></p>
</div></section>
""" + cta(),
     extra_ld=[faq_ld(HOME_FAQ)])

# ---- moving help
HELP_FAQ = [
    ("Do I need to rent the truck?", "<p>Most customers book their own truck or container and we load and unload it. Not sure what to book? Call and we will help you work it out.</p>"),
    ("Can I book just a load or just an unload?", "<p>Yes. Some jobs are one end only. Book us to load, to unload, or for both.</p>"),
    ("Can you come today?", "<p>Yes, we take same-day jobs. Call [[phone]] and we will tell you when a crew can get to you.</p>"),
    ("Do you bring equipment?", "<p>Yes. Hand trucks, dollies with straps and hand tools come with every job at no extra charge. Have moving blankets and tie-down straps on hand if you want furniture wrapped and secured in the truck.</p>"),
    ("Do you wrap furniture?", "<p>Yes, at no extra charge. Have moving blankets on hand and we wrap your furniture in them before it goes on the truck.</p>"),
    ("Can you load a PODS container or a storage unit?", "<p>Yes. We load and unload portable storage containers, such as PODS, and storage units, as well as rental trucks and trailers.</p>"),
    ("How far will you travel?", '<p>Up to about an hour and ten minutes from Wilmington. Jobs outside Wilmington may carry a travel fee. See the <a href="[[url:service-area]]">service area</a>.</p>'),
    ("How do I book and pay?", '<p>Call or text [[phone]], or send the <a href="[[url:contact]]">estimate form</a>. There is no deposit to book, and you can pay by cash, Venmo, or invoice.</p>'),
]
page("moving-help",
     "Moving Help in Wilmington, NC | Loading & Unloading Labor",
     "Hourly moving labor in Wilmington, NC. We load and unload rental trucks, trailers, PODS and storage units. Load only, unload only, or both: (704) 999-3714.",
     page_head("Moving help", "Moving help in Wilmington, NC: loading and unloading",
               "Hourly moving labor for the truck, trailer, storage unit or portable container you rent. We bring the crew to load it, unload it, or both. Book just one end if that is all you need.") + """
<section class="section"><div class="wrap cols cols--photo">
  <div class="stack-lg">
    <div class="stack">
      <h2>What our moving labor includes</h2>
      <ul>
        <li>A load only, an unload only, or both ends of the trip</li>
        <li>Carrying everything from your home to the truck or container</li>
        <li>Loading and stacking so the load stays put on the road</li>
        <li>Unloading at the other end and placing things in the right rooms</li>
        <li>Rental trucks, trailers, storage units and portable containers such as PODS</li>
        <li>Hand trucks, dollies with straps and hand tools, at no extra charge</li>
        <li>Wrapping your furniture in your moving blankets, at no extra charge</li>
      </ul>
    </div>
    <div class="stack">
      <h2>What to have ready</h2>
      <ul>
        <li>Moving blankets and tie-down straps, if you want furniture wrapped and secured. Most truck rental counters offer them.</li>
        <li>Boxes packed and taped before we arrive. We do not pack.</li>
        <li>Washers, dryers and fridges disconnected.</li>
      </ul>
    </div>
    <div class="stack">
      <h2>What moving help costs</h2>
      <p>We charge by the hour for the crew, with a minimum of two movers for two hours. The total depends on how much there is to carry, stairs and long walks to the truck.</p>
      <p>Call [[phone]] or send the form and we will quote your job. The estimate is free and there is no deposit to book.</p>
      <div class="actions"><a class="btn" href="[[url:contact|service=help]]">Get a free estimate</a></div>
    </div>
  </div>
  <figure class="photo">""" + pic("hand-truck-load", "A mover with a hand truck inside a loaded moving truck", S_SIDE, eager=True) + """</figure>
</div></section>

<section class="section section--band" id="truck"><div class="wrap cols">
  <div class="stack">
    <h2>What size moving truck should I rent?</h2>
    <p>Most customers book their own truck and we load it. This is how U-Haul sizes its trucks. Other rental companies use similar sizes.</p>
    <p>Between two sizes? Call [[phone]] and we will help you work it out.</p>
  </div>
  <div class="table-scroll"><table class="table--narrow">
    <thead><tr><th>Truck</th><th>What U-Haul says it fits</th></tr></thead>
    <tbody>
      <tr><td class="num">10 foot</td><td>Studio or 1 bedroom apartment</td></tr>
      <tr><td class="num">15 foot</td><td>1 bedroom home or 2 bedroom apartment</td></tr>
      <tr><td class="num">20 foot</td><td>2 bedroom home or 3 bedroom apartment</td></tr>
      <tr><td class="num">26 foot</td><td>3 to 4 bedroom home</td></tr>
    </tbody>
  </table>
  <p class="small">Sizes from """ + ext("https://www.uhaul.com/Truck-Rentals/", "U-Haul's truck rental page") + """, checked October 2026.</p></div>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>Trucks and containers we loaded</h2>
  <div class="strip strip--4">
    """ + pic("two-movers-boxes", "Two movers in front of boxes stacked floor to ceiling in a moving truck", S_STRIP) + """
    """ + pic("totes", "A mover giving two thumbs up in front of neatly stacked totes", S_STRIP) + """
    """ + pic("boxes-thumbs", "A mover giving two thumbs up in front of a wall of stacked moving boxes", S_STRIP) + """
    """ + pic("container", "A mover standing in front of a loaded portable storage container", S_STRIP) + """
  </div>
  <p>Want one crew to handle the whole move? See <a href="[[url:local-moving]]">local moving</a>. Moving a safe, a piano or a hot tub? See <a href="[[url:heavy-items]]">heavy items</a>.</p>
</div></section>

<section class="section section--band"><div class="wrap stack-lg">
  <h2>Questions about moving help</h2>
""" + faq_block(HELP_FAQ) + """
</div></section>
""" + cta("Need a crew for your truck?", "Tell us the date, both addresses and the size of the truck or container. We reply the same day during business hours."),
     crumb="Moving help",
     extra_ld=[service_ld("moving-help", "Moving help: loading and unloading", "Moving labor",
                          "Hourly loading and unloading help for rental trucks, trailers, storage units and portable containers in and around Wilmington, NC."),
               faq_ld(HELP_FAQ)])

# ---- local moving
LOCAL_FAQ = [
    ("Do you pick up and deliver on the same day?", "<p>Yes. Local moves around Wilmington are done in one trip, with the same crew at both ends.</p>"),
    ("What affects the price?", "<p>The size of the home, how much there is to move, stairs, long carries and heavy items.</p><p>We charge by the hour for the crew, with a minimum of two movers for two hours. Call [[phone]] or send the form and we will quote your job. There is no deposit to book.</p>"),
    ("Do you take furniture apart?", "<p>Yes. We take furniture apart and put it back together at the new place, and we bring the tools.</p>"),
    ("Can you move a safe, a piano or a hot tub?", '<p>Yes. We move gun safes, upright pianos, hot tubs and pool tables for an added fee. See <a href="[[url:heavy-items]]">heavy items</a>.</p>'),
    ("Do you pack for me?", "<p>No. We do not pack or supply boxes, so have everything boxed and taped before move day.</p>"),
    ("Which towns do you cover?", '<p>Wilmington and towns up to about an hour and ten minutes away. See the <a href="[[url:service-area]]">service area</a>.</p>'),
]
page("local-moving",
     "Local Movers in Wilmington, NC | Apartment, House & Office",
     "Local movers in Wilmington, NC for apartments, houses and offices. One crew, one trip, done the same day. Free estimates, no deposit: (704) 999-3714.",
     page_head("Local moving", "Local movers in Wilmington, NC",
               "Moving across town or across the river? One crew handles your apartment, house or office move from the first box to the last, on the same day.") + """
<section class="section"><div class="wrap cols cols--photo">
  <div class="stack-lg">
    <div class="stack">
      <h2>Apartment, house and office moves</h2>
      <ul>
        <li>Apartments and condos</li>
        <li>Houses</li>
        <li>Offices and small businesses</li>
      </ul>
      <p>Local moves around Wilmington are done in a single trip on the same day. The crew that loads you is the crew that unloads you.</p>
    </div>
    <div class="stack">
      <h2>What our movers do</h2>
      <ul>
        <li>Carries, loads and unloads everything</li>
        <li>Takes furniture apart and puts it back together at the new place, with our own tools</li>
        <li>Wraps furniture in your moving blankets</li>
        <li>Puts furniture and boxes in the rooms you choose</li>
      </ul>
    </div>
    <div class="stack" id="heavy">
      <h2>Heavy and awkward items</h2>
      <p>Gun safes, upright pianos, hot tubs and pool tables need extra hands and extra care, so each carries an added fee. Tell us about them when you ask for your estimate. More on the <a href="[[url:heavy-items]]">heavy items page</a>.</p>
    </div>
    <div class="stack">
      <h2>What a local move costs</h2>
      <p>We charge by the hour for the crew, with a minimum of two movers for two hours. The total depends on the size of your home, how much you have, stairs, long carries and heavy items.</p>
      <p>Call [[phone]] or send the form and we will quote your job. The estimate is free and there is no deposit to book.</p>
      <div class="actions"><a class="btn" href="[[url:contact|service=local]]">Get a free estimate</a></div>
    </div>
  </div>
  <div class="stack">
    <figure class="photo">""" + pic("crew-ramp", "Three crew members at the ramp of a packed moving truck", S_SIDE, eager=True) + """</figure>
    <figure class="photo">""" + pic("crew-straps", "Three crew members at the back of a truck with the load strapped down", S_SIDE) + """</figure>
  </div>
</div></section>

<section class="section section--band"><div class="wrap stack-lg">
  <div class="stack">
    <h2>Getting ready for move day</h2>
    <p>We charge by the hour, so a little preparation keeps the bill down.</p>
  </div>
  <div class="cols">
    <div class="stack">
      <h3>What we need from you</h3>
      <ul>
        <li>Everything boxed and taped before we arrive. We do not pack or supply boxes.</li>
        <li>Washers, dryers and fridges disconnected.</li>
        <li>Moving blankets, if you want furniture wrapped.</li>
        <li>A heads-up about anything heavy: safes, pianos, hot tubs, pool tables.</li>
      </ul>
    </div>
    <div class="stack">
      <h3>Tips that save time</h3>
      <ul>
        <li>Write the room on every box, so it goes to the right place the first time.</li>
        <li>Clear a path from the door to where the truck will park.</li>
        <li>If your building has an elevator or loading area to reserve, book it for move day.</li>
        <li>Keep keys, medicine and important papers with you, not in a box.</li>
      </ul>
    </div>
  </div>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>Questions about local moves</h2>
""" + faq_block(LOCAL_FAQ) + """
  <p>Renting your own truck instead? See <a href="[[url:moving-help]]">loading and unloading help</a>.</p>
</div></section>
""" + cta("Planning a move?", "Send both addresses, the number of bedrooms and your date. We reply with a price the same day during business hours."),
     crumb="Local moving",
     extra_ld=[service_ld("local-moving", "Local moving", "Local moving",
                          "Local moves for apartments, houses and offices in and around Wilmington, NC, done in one trip by one crew."),
               faq_ld(LOCAL_FAQ)])

# ---- heavy items
HEAVY_FAQ = [
    ("Which heavy items do you move?", "<p>Gun safes, upright pianos, hot tubs and pool tables.</p>"),
    ("Do you move grand pianos?", "<p>No. We move upright pianos only.</p>"),
    ("Can I book you for one heavy item, without a full move?", '<p>Yes. Pick "A heavy item moved" on the <a href="[[url:contact|service=heavy]]">estimate form</a>, or call [[phone]].</p>'),
    ("Why is there an added fee?", "<p>These items need extra hands and extra care. The fee depends on the item, so tell us about it when you ask for your estimate.</p>"),
    ("How far will you travel?", '<p>Up to about an hour and ten minutes from Wilmington. Jobs outside Wilmington may carry a travel fee. See the <a href="[[url:service-area]]">service area</a>.</p>'),
]
page("heavy-items",
     "Piano, Safe, Hot Tub & Pool Table Movers | Wilmington, NC",
     "Piano movers, gun safe movers, hot tub and pool table moving in Wilmington, NC. Extra hands for heavy items, alone or with a move: (704) 999-3714.",
     page_head("Heavy items", "Piano, gun safe, hot tub and pool table movers in Wilmington, NC",
               "Some things take more than two people and a dolly. We bring extra hands for the heavy and awkward ones, on their own or as part of a move.") + """
<section class="section"><div class="wrap cols">
  <div class="stack-lg">
    <div class="stack">
      <h2>Heavy items we move</h2>
      <p>We move four kinds of heavy item. Each one needs extra hands and extra care, so each carries an added fee.</p>
    </div>
    <div class="assure assure--one">
      <div><h3>Gun safe moving</h3><p>Tell us the make or the rough weight, and whether it has to go up or down any steps.</p></div>
      <div><h3>Upright piano moving</h3><p>We move uprights only, not grand pianos. Tell us about stairs and tight turns at both ends.</p></div>
      <div><h3>Hot tub moving</h3><p>Tell us the size, whether it is drained and disconnected, and how we reach it: gates, decks and steps.</p></div>
      <div><h3>Pool table moving</h3><p>Tell us the size of the table and which floor it is on.</p></div>
    </div>
  </div>
  <div class="stack">
    <div class="duo">
      """ + pic("pool-table", "Four crew members lifting a pool table with moving straps", "(max-width: 900px) 50vw, 270px", eager=True) + """
      """ + pic("piano", "Two movers carrying an upright piano through a house", "(max-width: 900px) 50vw, 270px", eager=True) + """
    </div>
    <p class="small">Two real jobs: a pool table and an upright piano.</p>
  </div>
</div></section>

<section class="section section--band"><div class="wrap cols">
  <div class="stack">
    <h2>What heavy item moving costs</h2>
    <p>Heavy items carry an added fee that depends on the item. Tell us what it is, where it sits now and where it is going, and we will give you a price. The estimate is free and there is no deposit to book.</p>
    <div class="actions"><a class="btn" href="[[url:contact|service=heavy]]">Get a free estimate</a><a class="tel" href="[[tel]]">[[phone]]</a></div>
  </div>
  <div class="stack">
    <h2>Part of a bigger move?</h2>
    <p>We can move a heavy item on its own or as part of a <a href="[[url:local-moving]]">local move</a>. If you are renting your own truck, see <a href="[[url:moving-help]]">loading and unloading help</a>.</p>
  </div>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>Questions about heavy items</h2>
""" + faq_block(HEAVY_FAQ) + """
</div></section>
""" + cta("Got something heavy?", "Tell us what it is and where it is going. We reply the same day during business hours."),
     crumb="Heavy items",
     extra_ld=[service_ld("heavy-items", "Piano, gun safe, hot tub and pool table moving", "Heavy item moving",
                          "Moving gun safes, upright pianos, hot tubs and pool tables in and around Wilmington, NC."),
               faq_ld(HEAVY_FAQ)])

# ---- service area
page("service-area",
     "Moving Service Area | Wilmington, NC & Nearby Towns",
     "Movers serving Wilmington, NC and towns up to about an hour away: Leland, Carolina Beach, Wrightsville Beach, Hampstead, Southport, Jacksonville and more.",
     page_head("Service area", "Movers serving Wilmington, NC and nearby towns",
               "We are based in Wilmington and travel up to about an hour and ten minutes in any direction.") + """
<section class="section"><div class="wrap stack-lg">
  <div class="towns">
    <div><h2>New Hanover</h2><ul><li>Wilmington, including downtown</li><li><a href="[[url:movers-carolina-beach-nc]]">Carolina Beach</a></li><li>Kure Beach</li><li><a href="[[url:movers-wrightsville-beach-nc]]">Wrightsville Beach</a></li><li>Castle Hayne</li><li>Figure Eight Island</li></ul></div>
    <div><h2>Brunswick</h2><ul><li><a href="[[url:movers-leland-nc]]">Leland</a></li><li>Southport</li><li>Oak Island</li><li>Boiling Spring Lakes</li><li>Winnabow</li><li>Bolivia</li></ul></div>
    <div><h2>Pender</h2><ul><li><a href="[[url:movers-hampstead-nc]]">Hampstead</a></li><li>Surf City</li><li>Topsail</li><li>Burgaw</li><li>Rocky Point</li></ul></div>
    <div><h2>Onslow</h2><ul><li>Jacksonville</li><li>Holly Ridge</li></ul></div>
    <div><h2>Columbus</h2><ul><li>Whiteville</li><li>Lake Waccamaw</li></ul></div>
  </div>
</div></section>
<section class="section section--band"><div class="wrap cols">
  <div class="stack">
    <h2>The travel fee</h2>
    <p>Jobs outside Wilmington may carry a travel fee. Tell us the town when you ask for your estimate and we will tell you whether one applies.</p>
  </div>
  <div class="stack">
    <h2>Not on the list?</h2>
    <p>If your town is within about an hour and ten minutes of Wilmington, we can most likely get to you. Call [[phone]] and ask.</p>
  </div>
</div></section>
<section class="section"><div class="wrap stack">
  <h2>Moving services in every town</h2>
  <p>The same three jobs: <a href="[[url:moving-help]]">loading and unloading help</a>, <a href="[[url:local-moving]]">local moves</a> and <a href="[[url:heavy-items]]">heavy items</a>.</p>
</div></section>
""" + cta(),
     crumb="Service area")

# ---- town pages. Each one says something true and specific about the town. Do not copy one and swap the name.
def town_page(slug, town, title, desc, lead, intro, tips, faq, photo, alt, nearby):
    tip_html = "".join("<div><h3>%s</h3><p>%s</p></div>" % t for t in tips)
    page(slug, title, desc,
         page_head(town, "Movers in %s, NC" % town, lead, parent=("service-area", "Service area")) + """
<section class="section"><div class="wrap cols cols--photo">
  <div class="stack-lg">
    <div class="stack">
      <h2>Moving services in %(town)s</h2>
      <p>%(intro)s</p>
      <ul>
        <li><a href="[[url:moving-help]]">Loading and unloading help</a> for rental trucks, trailers, storage units and portable containers. Book a load, an unload, or both.</li>
        <li><a href="[[url:local-moving]]">Local moves</a> for apartments, houses and offices, done in one trip by one crew</li>
        <li><a href="[[url:heavy-items]]">Heavy items</a>: gun safes, upright pianos, hot tubs and pool tables</li>
      </ul>
    </div>
    <div class="stack">
      <h2>What movers cost in %(town)s</h2>
      <p>We charge by the hour for the crew, with a minimum of two movers for two hours. %(town)s is outside Wilmington, so a travel fee may apply. Ask when you get your estimate. The estimate is free and there is no deposit to book.</p>
      <div class="actions"><a class="btn" href="[[url:contact]]">Get a free estimate</a><a class="tel" href="[[tel]]">[[phone]]</a></div>
    </div>
  </div>
  <figure class="photo">%(photo)s</figure>
</div></section>

<section class="section section--band"><div class="wrap stack-lg">
  <div class="stack">
    <h2>Good to know about moving in %(town)s</h2>
    <p>[[tbc:the three notes about %(town)s below. Fix anything that does not match what the crew sees there, or approve them.]]</p>
  </div>
  <div class="assure">%(tips)s</div>
  <p>%(nearby)s</p>
</div></section>

<section class="section"><div class="wrap stack-lg">
  <h2>Questions about moving in %(town)s</h2>
%(faq)s
</div></section>
""" % dict(town=town, intro=intro, tips=tip_html, faq=faq_block(faq), nearby=nearby,
           photo=pic(photo, alt, S_SIDE, eager=True)) + cta("Moving in %s?" % town, "Tell us what needs moving and when. We reply the same day during business hours."),
         crumb=town, parent=("service-area", "Service area"),
         extra_ld=[service_ld(slug, "Movers in %s, NC" % town, "Moving labor and local moving",
                              "Loading and unloading help, local moves and heavy item moving in %s, NC." % town),
                   faq_ld(faq)])


FEE_Q = lambda town: ("Is there a travel fee for %s?" % town, "<p>%s is outside Wilmington, so a travel fee may apply. Ask when you get your estimate.</p>" % town)

town_page("movers-leland-nc", "Leland",
          "Movers in Leland, NC | Express Movers",
          "Movers in Leland, NC for local moves, loading and unloading help, and heavy items. Rated 4.9 stars on Google. Free estimates: (704) 999-3714.",
          "Leland is just across the Cape Fear River from downtown Wilmington, in Brunswick County. Our crew of UNC Wilmington students loads, unloads and moves homes there.",
          "The same three jobs we do in Wilmington:",
          [("The bridges back up", "The bridges between Wilmington and Leland slow down at rush hour. A mid-morning start avoids the worst of it."),
           ("Check your community's rules", "Planned communities such as Brunswick Forest, Waterford and Magnolia Greens can have their own rules for moving trucks. Ask your HOA or gatehouse before move day."),
           ("Arriving with a truck or a container?", "If you are moving in with a rental truck or a portable container, we unload it, carry everything to the right rooms and put the furniture back together.")],
          [FEE_Q("Leland"),
           ("Can you unload a truck or container in Leland?", "<p>Yes. We unload rental trucks, trailers and portable containers, and we load them too.</p>"),
           ("Do you work elsewhere in Brunswick County?", '<p>Yes. We also work in Southport, Oak Island, Boiling Spring Lakes, Winnabow and Bolivia. See the <a href="[[url:service-area]]">service area</a>.</p>')],
          "crew-two", "Two crew members giving a thumbs up in a loaded moving truck",
          'We also work across the river in <a href="[[url:index]]">Wilmington</a> and in the rest of Brunswick County. See the <a href="[[url:service-area]]">full service area</a>.')

town_page("movers-carolina-beach-nc", "Carolina Beach",
          "Movers in Carolina Beach, NC | Express Movers",
          "Movers in Carolina Beach and Kure Beach, NC for local moves, loading and unloading help, and heavy items. Free estimates: (704) 999-3714.",
          "Carolina Beach is on Pleasure Island, south of Wilmington. Our crew of UNC Wilmington students loads, unloads and moves homes and condos there and next door in Kure Beach.",
          "The same three jobs we do in Wilmington:",
          [("One bridge on and off", "US 421 over Snow's Cut is the only bridge onto the island, and it slows down on summer weekends. Weekday mornings are easier."),
           ("Raised houses mean stairs", "Many beach houses and condos sit a floor or more above the ground. Tell us how many flights there are and whether there is an elevator, because stairs change how long a job takes."),
           ("Plan where the truck parks", "Space is tight near the beach. Work out where the truck can park before move day, and ask your rental office or HOA about move-in rules.")],
          [FEE_Q("Carolina Beach"),
           ("Do you carry furniture up beach house stairs?", "<p>Yes. Stairs are part of the job. Tell us how many flights there are when you ask for your estimate.</p>"),
           ("Do you also work in Kure Beach?", "<p>Yes. Kure Beach is on the same island and we work there too.</p>")],
          "load-pair", "Two movers standing in front of a packed load in a moving truck",
          'We also work in Kure Beach and back over the bridge in <a href="[[url:index]]">Wilmington</a>. See the <a href="[[url:service-area]]">full service area</a>.')

town_page("movers-wrightsville-beach-nc", "Wrightsville Beach",
          "Movers in Wrightsville Beach, NC | Express Movers",
          "Movers in Wrightsville Beach, NC for local moves, loading and unloading help, and heavy items. Rated 4.9 on Google. Free estimates: (704) 999-3714.",
          "Wrightsville Beach is just over the Heide Trask Drawbridge from Wilmington. Our crew of UNC Wilmington students loads, unloads and moves homes and condos there.",
          "The same three jobs we do in Wilmington:",
          [("The drawbridge opens for boats", "When the Heide Trask Drawbridge goes up, traffic onto the island stops. Leave a little slack in your timing."),
           ("Parking is metered most of the year", "The town meters its parking from March 1 to October 31, and spaces fill up in summer. Line up a spot for the truck before move day."),
           ("Tell us about the stairs", "Many beach houses and condos sit a floor or more above the ground. Tell us how many flights there are and whether there is an elevator.")],
          [FEE_Q("Wrightsville Beach"),
           ("Where will the truck park?", "<p>That is worth sorting out before move day. The town meters its parking from March 1 to October 31, so ask your landlord, rental office or HOA where a moving truck can go.</p>"),
           ("Do you carry furniture up outside stairs?", "<p>Yes. Stairs are part of the job. Tell us how many flights there are when you ask for your estimate.</p>")],
          "mattress", "A mover giving a thumbs up next to a mattress and totes loaded in a truck",
          'We also work back over the bridge in <a href="[[url:index]]">Wilmington</a>. See the <a href="[[url:service-area]]">full service area</a>.')

town_page("movers-hampstead-nc", "Hampstead",
          "Movers in Hampstead, NC | Express Movers",
          "Movers in Hampstead, NC for local moves, loading and unloading help, and heavy items. Rated 4.9 stars on Google. Free estimates: (704) 999-3714.",
          "Hampstead is up US 17 from Wilmington, in Pender County. Our crew of UNC Wilmington students loads, unloads and moves homes there.",
          "The same three jobs we do in Wilmington:",
          [("US 17 is the way in and out", "US 17 through Hampstead is busy at commuting times. A mid-morning start avoids the worst of it."),
           ("Tell us how close the truck can get", "If the truck cannot park near the door, let us know. A long carry adds time."),
           ("Heading farther up the coast?", "We also work in Surf City, Topsail and Holly Ridge, so a move from Hampstead toward the beach is in our area.")],
          [FEE_Q("Hampstead"),
           ("Do you go as far as Surf City and Topsail?", '<p>Yes. Both are inside our area, which reaches about an hour and ten minutes from Wilmington. See the <a href="[[url:service-area]]">service area</a>.</p>'),
           ("Can you load a storage unit in Hampstead?", "<p>Yes. We load and unload storage units and portable containers as well as trucks and trailers.</p>")],
          "dresser", "A mover giving a thumbs up in front of a dresser and bins loaded in a truck",
          'We also work in Surf City, Topsail, Burgaw and Rocky Point. See the <a href="[[url:service-area]]">full service area</a>.')

# ---- reviews
page("reviews",
     "Express Movers Reviews | Wilmington, NC Movers",
     "Express Movers is rated 4.9 stars on Google, with 685 reviews across three review sites. Read what moving customers in Wilmington, NC wrote.",
     page_head("Reviews", "Express Movers reviews",
               "Rated 4.9 stars on Google by moving customers around Wilmington, NC. We would rather you read reviews where customers wrote them than take our word for it.") + """
<section class="section"><div class="wrap stack-lg">
  <div class="table-scroll"><table>
    <thead><tr><th>Where</th><th>Rating</th><th>Reviews</th></tr></thead>
    <tbody>
      <tr><td>""" + ext("[[google]]", "Google") + """</td><td class="num">4.9 stars</td><td class="num">53</td></tr>
      <tr><td>HireAHelper</td><td class="num">4.9 stars</td><td class="num">155</td></tr>
      <tr><td>U-Haul Moving Help</td><td>No star rating shown</td><td class="num">477</td></tr>
    </tbody>
  </table></div>
  <p class="small">Counted [[counted]].</p>
  <div class="stack">
    <h2>What three customers wrote</h2>
    <p>Copied word for word from Google.</p>
  </div>
""" + quotes_block() + """
  <div class="stack">
    <h2>Moved by us?</h2>
    <p>A Google review helps a small crew more than anything else you can do.</p>
    <div class="actions">""" + '<a class="btn" href="[[google]]" target="_blank" rel="noopener noreferrer">Leave a Google review</a>' + """</div>
  </div>
</div></section>
""" + cta(),
     crumb="Reviews")

# ---- about
page("about",
     "About Express Movers | Wilmington, NC Moving Company",
     "Express Movers LLC is a Wilmington, NC moving company founded by Jared Mazzola in October 2021, with a crew of more than 15 UNC Wilmington students.",
     page_head("About", "A Wilmington moving company crewed by UNCW students",
               "Jared Mazzola started Express Movers in October 2021. Everyone who shows up at your door is a student at UNC Wilmington.") + """
<section class="section"><div class="wrap cols">
  <div class="stack-lg">
    <div class="stack">
      <h2>Why it works</h2>
      <p>Moving is hard physical work with a start time and an end time. That suits students. We fit jobs around classes, we work weekends, and we would rather carry a couch than sit at a desk.</p>
      <p>Jared trains every crew member himself. The crew has grown to more than 15 students, so we can staff small jobs and big ones on the same day.</p>
    </div>
    <dl class="facts">
      <div><dt>Founder</dt><dd>Jared Mazzola</dd></div>
      <div><dt>Started</dt><dd>October 2021</dd></div>
      <div><dt>Crew</dt><dd>More than 15 UNC Wilmington students</dd></div>
      <div><dt>Based in</dt><dd>Wilmington, NC 28403</dd></div>
      <div><dt>Hours</dt><dd>Every day, 8am to 7pm</dd></div>
    </dl>
  </div>
  <div class="stack">
    <figure class="photo photo--land">""" + pic("crew-storage", "Four Express Movers crew members in front of a fully loaded truck beside a row of storage units", "(max-width: 900px) 100vw, 560px", eager=True) + """</figure>
    <div class="strip strip--2">
      """ + pic("crew-three", "Three crew members in front of an open moving truck", "(max-width: 900px) 50vw, 275px") + """
      """ + pic("hoodies", "Two crew members giving a thumbs up at the back of a loaded truck", "(max-width: 900px) 50vw, 275px") + """
    </div>
  </div>
</div></section>
<section class="section section--band"><div class="wrap bio">
  <figure class="photo">""" + pic("jared", "Jared Mazzola, founder of Express Movers", "(max-width: 760px) 60vw, 300px") + """</figure>
  <div class="stack">
    <h2>Meet Jared</h2>
    <p class="lead">Jared Mazzola founded Express Movers in October 2021. At first he expected it to be side work to help pay for tuition at UNCW and living costs.</p>
    <p>By the spring of 2022 the company's reputation had grown fast, and so had the crew, filled with hard-working UNCW students. Express Movers has been his career ever since, and he now manages a crew of more than 15 UNCW students.</p>
    <p><b>Jared Mazzola</b>, founder</p>
  </div>
</div></section>
<section class="section"><div class="wrap cols">
  <div class="stack">
    <h2>Check us before you call</h2>
    <p>We have done more than 700 moves since October 2021, and customers rate us 4.9 stars on Google.</p>
    <p><a href="[[url:reviews]]">Read Express Movers reviews</a>.</p>
  </div>
  <div class="stack">
    <h2>Our moving services</h2>
    <p><a href="[[url:moving-help]]">Loading and unloading help</a>, <a href="[[url:local-moving]]">local moves</a> and <a href="[[url:heavy-items]]">heavy items</a>, in Wilmington and towns up to about an hour and ten minutes away.</p>
    <p><a href="[[url:gallery]]">See photos from the job</a>.</p>
  </div>
</div></section>
""" + cta(),
     crumb="About")

# ---- gallery
GALLERY = [("tailgate-tall", "Five crew members on the tailgate of a loaded moving truck"),
           ("crew-ramp", "Three crew members at the ramp of a packed truck"),
           ("crew-straps", "Three crew members at the back of a truck with the load strapped down"),
           ("crew-three", "Three crew members in front of an open moving truck"),
           ("uncw-boxes", "A mover in a UNCW shirt in front of boxes stacked to the ceiling"),
           ("two-movers-boxes", "Two movers in front of boxes stacked floor to ceiling"),
           ("ramp-uncw", "Two movers on a truck ramp, one wearing a UNCW shirt"),
           ("crew-two", "Two crew members giving a thumbs up in a loaded truck"),
           ("hand-truck-load", "A mover with a hand truck inside a loaded truck"),
           ("hand-truck-boxes", "A mover with a hand truck in front of boxes and wrapped furniture"),
           ("ramp-hand-truck", "A mover wheeling stacked boxes down a truck ramp on a hand truck"),
           ("pool-table", "Four crew members lifting a pool table with moving straps"),
           ("totes", "A mover in front of neatly stacked totes"),
           ("boxes-thumbs", "A mover in front of a wall of stacked boxes"),
           ("boxes-wrapped", "A mover next to wrapped furniture and stacked boxes"),
           ("container", "A mover in front of a loaded portable storage container"),
           ("load-two", "Two movers inside a packed truck with wrapped furniture"),
           ("load-pair", "Two movers in front of a packed load"),
           ("hoodies", "Two crew members at the back of a loaded truck"),
           ("mattress", "A mover next to a mattress and totes loaded in a truck"),
           ("thumbs-ladder", "A mover giving two thumbs up in a loaded truck"),
           ("dresser", "A mover in front of a dresser and bins loaded in a truck"),
           ("boxes-yellow", "A mover in front of moving boxes loaded in a truck"),
           ("loaded-thumbs", "A mover giving two thumbs up in a fully loaded truck")]
page("gallery",
     "Moving Photos | Express Movers, Wilmington, NC",
     "Photos from real Express Movers jobs around Wilmington, NC: the crew, loaded trucks, storage containers and heavy items. No stock photos.",
     page_head("Photos", "Photos from the job", "Real jobs and real crew members around Wilmington. No stock photos.") + """
<section class="section"><div class="wrap stack-lg">
  <div class="strip strip--4">""" + "".join(pic(n, a, S_STRIP, eager=(i < 4)) for i, (n, a) in enumerate(GALLERY)) + """</div>
  <p>See what the crew does on <a href="[[url:moving-help]]">moving help</a> jobs, <a href="[[url:local-moving]]">local moves</a> and <a href="[[url:heavy-items]]">heavy items</a>.</p>
</div></section>
""" + cta(),
     crumb="Photos")

# ---- faq
FAQ_GROUPS = [
    ("The crew", [
        ("Who does the moving?", "<p>Students from UNC Wilmington, each one trained by founder Jared Mazzola. The same crew handles your job from start to finish.</p>"),
        ("How long has Express Movers been around?", "<p>Since October 2021.</p>"),
        ("Are you insured?", "<p>Our crew is covered by workers' compensation insurance.</p>"),
    ]),
    ("Booking and price", [
        ("How do I get an estimate?", '<p>Call [[phone]] or send the <a href="[[url:contact]]">estimate form</a>. We ask about both addresses, the number of bedrooms, stairs and any heavy items. The estimate is free.</p>'),
        ("How fast will you reply?", "<p>The same day when you reach us between 8am and 7pm. Requests sent after 7pm get a reply the next day.</p>"),
        ("How much do movers cost?", "<p>We charge by the hour for the crew, with a minimum of two movers for two hours. The total depends on the size of the job, stairs, long carries and heavy items. Call [[phone]] or send the form for a free quote.</p>"),
        ("Is there a minimum?", "<p>Yes. The minimum booking is two movers for two hours.</p>"),
        ("Do you take same-day jobs?", "<p>Yes. Call [[phone]] and we will tell you when a crew can get to you.</p>"),
        ("Is there a deposit?", "<p>No. There is no deposit to book.</p>"),
        ("How do I pay?", "<p>Cash, Venmo, or invoice.</p>"),
        ("How do I book?", '<p>Call or text [[phone]], or send the <a href="[[url:contact]]">estimate form</a>. We confirm your date and time directly with you.</p>'),
        ("When are you open?", "<p>Every day of the week, 8am to 7pm.</p>"),
        ("Where do you work?", '<p>Wilmington and towns up to about an hour and ten minutes away, including Leland, Carolina Beach, Hampstead, Southport, Burgaw, Jacksonville and Whiteville. Jobs outside Wilmington may carry a travel fee. See the <a href="[[url:service-area]]">service area</a>.</p>'),
    ]),
    ("Move day", [
        ("Do you finish a local move in one day?", "<p>Yes. Local moves around Wilmington are done in a single trip on the same day, with the same crew at both ends.</p>"),
        ("Do I need to rent the truck?", '<p>For loading and unloading help, most customers book their own truck or container and we load and unload it. See the <a href="[[url:moving-help#truck]]">truck size guide</a>, or call and we will help you work it out.</p>'),
        ("Can I book just a load or just an unload?", "<p>Yes. Book us to load, to unload, or for both.</p>"),
        ("Do you load storage units and portable containers?", "<p>Yes, as well as rental trucks and trailers.</p>"),
        ("What equipment do you bring?", "<p>Hand trucks, dollies with straps and hand tools, at no extra charge. Have moving blankets and tie-down straps on hand if you want furniture wrapped and secured.</p>"),
        ("Do you wrap furniture?", "<p>Yes, at no extra charge. Have moving blankets on hand and we wrap your furniture in them.</p>"),
        ("Do you pack?", "<p>No. We do not pack or supply boxes. We do take furniture apart and put it back together.</p>"),
        ("Do I need to disconnect my appliances?", "<p>Yes. Disconnect washers, dryers and fridges before the crew arrives.</p>"),
    ]),
    ("Heavy items", [
        ("Do you move pianos, safes or hot tubs?", '<p>Yes. We move gun safes, upright pianos, hot tubs and pool tables for an added fee. See <a href="[[url:heavy-items]]">heavy items</a>.</p>'),
        ("Can I book you for one heavy item?", "<p>Yes. A heavy item can be moved on its own or as part of a bigger move.</p>"),
        ("Do you move grand pianos?", "<p>No. We move upright pianos only.</p>"),
    ]),
]
FAQ_ALL = [qa for _, items in FAQ_GROUPS for qa in items]
page("faq",
     "Moving FAQ: Prices, Booking & Move Day | Wilmington, NC",
     "Answers about hiring movers in Wilmington, NC: what movers cost, the two-hour minimum, same-day jobs, what to have ready, and moving heavy items.",
     page_head("Questions", "Moving questions and answers", "If yours is not here, call [[phone]].") + """
<section class="section"><div class="wrap stack-lg">
""" + "\n".join('<div class="faq-group"><h2>%s</h2>\n%s</div>' % (g, faq_block(items)) for g, items in FAQ_GROUPS) + """
  <p>More detail is on the <a href="[[url:moving-help]]">moving help</a>, <a href="[[url:local-moving]]">local moving</a>, <a href="[[url:heavy-items]]">heavy items</a> and <a href="[[url:service-area]]">service area</a> pages.</p>
</div></section>
""" + cta(),
     crumb="Questions", extra_ld=[faq_ld(FAQ_ALL)])

# ---- contact
page("contact",
     "Free Moving Estimate in Wilmington, NC | Express Movers",
     "Get a free moving estimate in Wilmington, NC for a local move, loading and unloading help or a heavy item. Call (704) 999-3714 or send the form.",
     page_head("Free estimate", "Get a free moving estimate", "Call or text us, or send the details. We reply the same day during business hours. No deposit to book.") + """
<section class="section"><div class="wrap cols">
  <form class="ticket" id="estimate-form" novalidate data-action="%(form_action)s" data-done="[[url:thank-you]]" data-phone="[[phone]]">
    <div class="ticket-head"><h2>Estimate request</h2><span class="small">Free. No deposit to book.</span></div>
    <div class="ticket-body">
      <div class="field"><label for="f-name">Name</label><input id="f-name" name="name" type="text" autocomplete="name" maxlength="80" required></div>
      <div class="field"><label for="f-phone">Phone</label><input id="f-phone" name="phone" type="tel" inputmode="tel" autocomplete="tel" maxlength="20" required></div>
      <div class="field field--wide"><label for="f-email">Email (optional)</label><input id="f-email" name="email" type="email" autocomplete="email" maxlength="120"></div>
      <fieldset class="chips field--wide">
        <legend>What do you need?</legend>
        <div class="chip-row">
          <label class="chip"><input type="radio" id="f-service-help" name="service" data-key="help" value="Loading or unloading help" checked><span>Loading or unloading help</span></label>
          <label class="chip"><input type="radio" id="f-service-local" name="service" data-key="local" value="A local move"><span>A local move</span></label>
          <label class="chip"><input type="radio" id="f-service-heavy" name="service" data-key="heavy" value="A heavy item moved"><span>A heavy item moved</span></label>
          <label class="chip"><input type="radio" id="f-service-unsure" name="service" data-key="unsure" value="Not sure yet"><span>Not sure yet</span></label>
        </div>
      </fieldset>
      <div class="field"><label for="f-from">From (town or zip)</label><input id="f-from" name="from" type="text" maxlength="80"></div>
      <div class="field"><label for="f-to">To (town or zip)</label><input id="f-to" name="to" type="text" maxlength="80"></div>
      <div class="field field--wide"><label for="f-date">Date</label><input id="f-date" name="date" type="date"></div>
      <div class="field field--wide"><label for="f-details">Details</label><textarea id="f-details" name="details" maxlength="1500" placeholder="Number of bedrooms, stairs, heavy items, truck or container size"></textarea></div>
      <div class="hp" aria-hidden="true"><label for="f-gotcha">Leave this empty</label><input id="f-gotcha" name="_gotcha" type="text" tabindex="-1" autocomplete="off"></div>
      <label class="consent field--wide"><input id="f-sms" name="sms_consent" type="checkbox" value="yes"><span>I agree to receive text messages from [[legal]] about my estimate at the number above. Message and data rates may apply. Message frequency varies. Reply STOP to opt out or HELP for help. Consent is not a condition of purchase. See the <a href="[[url:privacy]]">privacy policy</a>.</span></label>
      <div class="field--wide stack">
        <div class="actions"><button class="btn" type="submit">Send my request</button></div>
        <p class="form-note" id="form-note" role="status" hidden></p>
      </div>
    </div>
  </form>
  <div class="stack-lg">
    <div class="stack">
      <h2>Or call</h2>
      <a class="tel" href="[[tel]]">[[phone]]</a>
      <p>[[hours]].</p>
      <p>Email: <a href="mailto:[[email]]">[[email]]</a></p>
      <p>Reach us between 8am and 7pm and we reply the same day. Requests sent after 7pm get a reply the next day.</p>
      <p>Need a crew today? Call. We take same-day jobs.</p>
    </div>
    <div class="stack">
      <h2>Have this ready</h2>
      <ul>
        <li>Both addresses, or the towns</li>
        <li>How many bedrooms</li>
        <li>Stairs or elevators at either end</li>
        <li>Anything heavy: safes, pianos, hot tubs, pool tables</li>
        <li>The size of the truck or container, if you already booked one</li>
      </ul>
    </div>
    <p>[[legal]], Wilmington, NC 28403. See the <a href="[[url:service-area]]">service area</a>.</p>
  </div>
</div></section>
""" % {"form_action": html.escape(SITE["form_action"], quote=True)},
     crumb="Free estimate")

# ---- thank you
page("thank-you",
     "Request Sent | Express Movers",
     "Your estimate request reached Express Movers.",
     """<section class="section"><div class="wrap stack">
  <h1>Request sent</h1>
  <p class="lead">Thanks. We have your details and will get back to you with a price.</p>
  <p>Requests sent between 8am and 7pm get a reply the same day. After 7pm, we reply the next day.</p>
  <p>Need to reach us sooner? Call or text <a href="[[tel]]">[[phone]]</a>. [[hours]].</p>
  <div class="actions"><a class="btn" href="[[url:index]]">Back to the homepage</a><a class="btn btn--quiet" href="[[url:faq]]">Read common questions</a></div>
</div></section>""",
     index=False, lead=True, in_sitemap=False)

# ---- privacy
page("privacy",
     "Privacy Policy | Express Movers",
     "How Express Movers LLC collects and uses information sent through this website.",
     page_head("Privacy", "Privacy policy", "Updated [[updated]].") + """
<section class="section"><div class="wrap stack-lg narrow">
  <div class="stack"><h2>What we collect</h2>
    <p>When you send the estimate form we collect what you type into it: your name, phone number, email address if you give one, the addresses or towns involved, your date and any details about the job. When you call, text or email us we receive your phone number or email address.</p></div>
  <div class="stack"><h2>How we use it</h2>
    <p>We use it to give you an estimate, schedule your job, and contact you about it. We do not sell your information.</p></div>
  <div class="stack"><h2>Text messages</h2>
    <p>If you tick the box on the estimate form, you agree to receive text messages from [[legal]] about your estimate and your job. Message frequency varies. Message and data rates may apply. Reply STOP to stop messages at any time, or HELP for help. Agreeing to texts is not a condition of buying anything.</p>
    <p>We do not share mobile numbers or text message consent with third parties or affiliates for their marketing.</p></div>
  <div class="stack"><h2>Who else sees it</h2>
    <p>We use service providers to run the website, receive form submissions and send messages. They handle your information only to provide those services to us.</p></div>
  <div class="stack"><h2>Your choices</h2>
    <p>You can ask us what information we hold about you, or ask us to delete it, by emailing <a href="mailto:[[email]]">[[email]]</a> or calling [[phone]].</p></div>
  [[preview:This policy is a plain summary and is not legal advice. Have a lawyer review it before launch. If analytics or a Meta Pixel is switched on, this page needs a section about it first.]]
</div></section>""",
     crumb="Privacy")

# ---- terms
page("terms",
     "Website Terms | Express Movers",
     "Terms for using the Express Movers LLC website.",
     page_head("Terms", "Website terms", "Updated [[updated]]. These terms cover this website only. The terms of a moving job are agreed with you when you book.") + """
<section class="section"><div class="wrap stack-lg narrow">
  <div class="stack"><h2>Who runs this site</h2>
    <p>This website is run by [[legal]], Wilmington, NC 28403. You can reach us at [[phone]] or <a href="mailto:[[email]]">[[email]]</a>.</p></div>
  <div class="stack"><h2>Information on this site</h2>
    <p>The site describes our services in general terms. Ratings and review counts were counted on the date shown next to them and change over time. We quote a price for each job, so nothing on this site is a price.</p></div>
  <div class="stack"><h2>Photos and text</h2>
    <p>The photos and text on this site belong to [[legal]]. Ask us before you reuse them.</p></div>
  <div class="stack"><h2>Links to other sites</h2>
    <p>We link to Google, U-Haul, Facebook, YouTube and Pinterest so you can read reviews, check truck sizes and see our pages there. Those sites are run by other companies under their own terms.</p></div>
  <div class="stack"><h2>Using the estimate form</h2>
    <p>Send only true information about your own job. Do not use the form to send spam or harmful content. If your misuse of this site causes a loss to [[legal]], you agree to cover it.</p></div>
  <div class="stack"><h2>Liability for the website</h2>
    <p>We work to keep this site accurate and available, but it is provided as it is. As far as the law allows, [[legal]] is not liable for losses that come from using the website itself, such as the site being unavailable.</p></div>
  <div class="stack"><h2>Governing law</h2>
    <p>These terms are governed by the laws of the State of North Carolina.</p></div>
  <div class="stack"><h2>Changes</h2>
    <p>We may update these terms. The date at the top shows the latest version.</p></div>
  [[preview:These terms are a plain draft and are not legal advice. Have a lawyer review the liability, misuse and governing law sections before launch.]]
</div></section>""",
     crumb="Terms")

# ---- 404
page("404",
     "Page not found | Express Movers",
     "That page does not exist.",
     """<section class="section"><div class="wrap stack">
  <h1>That page moved out</h1>
  <p class="lead">The link is old or mistyped. These are still here.</p>
  <div class="actions"><a class="btn" href="[[url:index]]">Back to the homepage</a><a class="btn btn--quiet" href="[[url:contact]]">Get a free estimate</a></div>
  <p><a href="[[url:moving-help]]">Moving help</a>, <a href="[[url:local-moving]]">local moving</a>, <a href="[[url:heavy-items]]">heavy items</a>, <a href="[[url:service-area]]">service area</a>.</p>
</div></section>""",
     index=False, in_sitemap=False)


# ------------------------------------------------------------------ launch checklist (preview only)
def checklist_body():
    confirm = "".join("<tr><td>%s</td><td>%s</td></tr>" % (html.escape(n[0].upper() + n[1:]), s) for s, n in NOTES) \
        or "<tr><td>Nothing open.</td><td></td></tr>"

    def rows(items):
        return "".join("<tr><td><b>%s</b></td><td>%s</td></tr>" % r for r in items)
    listing = [
        ("Every crew member is trained by Jared", "His HireAHelper listing says: \"All my crew members are personally trained by me, Jared Mazzola.\" Used on the homepage, about page and questions page."),
        ("Equipment comes with every job at no charge", "The listing says hand truck, dolly and dolly straps, and hand tools are always included, and that the crew wraps the customer's blankets around furniture at no charge. Used on the homepage and service pages. Confirm the same holds when a customer books direct."),
        ("A heavy item can be booked on its own", "Assumed from the choice on the estimate form. The heavy items page says a safe, piano, hot tub or pool table can be moved without a full move."),
        ("More than 700 moves and 685 reviews", "The site says \"more than 700 moves since October 2021\", based on the 731 moves the HireAHelper listing showed on October 8, 2026. The 685 reviews add up Google (53), HireAHelper (155) and U-Haul Moving Help (477). Recount before launch."),
    ]
    ask = [
        ("More reviews to quote", "Jared is finding these. Send screenshots of any HireAHelper or U-Haul reviews you want featured, word for word."),
        ("Larger copies of three photos", "Jared is finding these. The pool table, the piano and the hand truck on the ramp are small files."),
        ("Two listings now say different things", "This site says same-day jobs are taken. The HireAHelper listing says same-day requests are not accepted. Decide whether to update the listing."),
    ]
    answered = [
        ("Minimum booking", "Two movers for two hours. On the service pages, the town pages and the questions page."),
        ("Same-day jobs", "Yes. On the homepage, the contact page and the questions pages."),
        ("How long jobs take", "Left out, as asked."),
        ("Travel fee", "The site now says jobs outside Wilmington may carry a travel fee."),
        ("Pianos", "Uprights only. The heavy items page and the questions page say no grand pianos."),
        ("Jared's story and photo", "On the about page, from the text and photo sent on October 8. The crew size is now more than 15 everywhere."),
        ("Damaged items", "Taken off the site, as asked. No page mentions damage or what happens if something breaks."),
        ("Booking through other sites", "Taken off, as asked, because booking direct earns more. Every page sends customers to call, text or the estimate form. No page links to HireAHelper or U-Haul Moving Help. The reviews page still names both, unlinked, with their review counts."),
        ("Wording tuned for search", "Every page title, description and main heading now leads with what people type into Google, such as \"movers in Wilmington, NC\", \"moving help\", \"local movers\" and \"piano movers\". The student crew stays as the reason to pick Express Movers."),
    ]
    domain = [
        ("Domain transfer is under way", "Ordered at Namecheap in Jared's account on October 8, 2026. The public record shows it as pending transfer. Reply to the Townsquare support email and ask them to approve the outgoing transfer, or wait 5 to 7 days."),
        ("Ask Townsquare for the shutoff date", "The current site and its DNS both run on their side. The new site has to be live before they switch off, or the address goes dark."),
        ("Point the domain at GitHub Pages", "After the transfer completes, at Namecheap: four A records for @ (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153) and one CNAME for www pointing at the GitHub account's github.io name. Then set the custom domain to www.expressmoversilm.com in the repo's Pages settings and tick Enforce HTTPS."),
        ("Read the Townsquare contract before the cancellation is final", "Check the term, the notice period and any cancellation fee. The phone number is Jared's own, so that is safe. This is not legal advice."),
    ]
    safety = [
        ("Turn on two-factor sign-in", "On the GitHub account that holds this site, on the Namecheap account and on the Google account that owns the Business Profile. Save the recovery codes somewhere offline."),
        ("Verify the domain inside GitHub", "Account settings, Pages, Add a domain. It stops anyone else from attaching the address to their own GitHub site."),
        ("Lock the domain and turn on auto-renew", "Both are switches at Namecheap once the transfer lands. Swap the saved card for Jared's own."),
        ("Share ownership with Jared", "Keep the domain in his name and add him as an owner on the repo, or keep the repo in an organization you both control."),
        ("Keep secrets out of the repo", "The repo is public. A form address or an analytics ID is fine there. Passwords, API keys and private tokens are not."),
        ("What the site already does", "Every page ships with a content security policy that only runs this site's own script and blocks frames, plugins and injected code. Fonts are stored on the site, so no visitor data goes to a font service. The form has a hidden spam trap and length limits. Outside links cannot reach back into the page."),
        ("One limit to know", "GitHub Pages cannot send security headers, so the policy is set in the page itself. That covers scripts and content, but it cannot stop another site from showing this one inside a frame. Putting Cloudflare in front of the site later would close that gap."),
    ]
    launch = [
        ("Connect the estimate form", "It is switched off in this preview. Put the form address in form_action at the top of build.py. A Formspree form works as is, and the consent line is already on the form."),
        ("Check the three quoted customers are fine with it", "Josiah, Ryan and Davis are quoted word for word from public Google reviews, first name only. A quick text from Jared asking each of them is the polite move. Davis mentions free extra pieces, so decide whether that is an expectation you want on the homepage."),
        ("Replace the tab icon", "The icon in the browser tab is a stand-in drawn from the three bars in the logo."),
        ("Add analytics", "Google Analytics and the Meta Pixel are off. Create both for Express Movers, put the IDs in build.py, and add a section to the privacy policy first. Do not reuse another business's pixel."),
        ("Have a lawyer read the privacy policy and the website terms", "Both are plain drafts. This is not legal advice."),
        ("Add Zane as a manager on the Google Business Profile", "Confirm Jared's own Google account is the primary owner, then remove Townsquare's access. Then fill in the services list, post weekly with a link to the matching page here, and keep the name, address and phone identical to this site."),
        ("Submit the sitemap", "Add the site in Google Search Console and submit /sitemap.xml once the domain points here. Expect about 30 days before search results settle."),
    ]
    choices = [
        ("The truck is not advertised, and the state rule behind that", "By Jared's choice the site sells the crew and does not mention his truck or truck rates. North Carolina law (G.S. 62-280.1) makes it unlawful to carry household goods for pay within the state without a certificate from the Utilities Commission, with fines up to $2,000 and a civil penalty up to $5,000. The Commission's guide lists office moves as outside its rules, and loading a truck the customer rents is labor, not carrying. The site does not claim a certificate anywhere. If Express Movers ever carries a household's goods in its own truck, a call to the Commission at 919-733-7766 would settle whether that needs one. This is not legal advice."),
        ("Insurance wording", "The old site said \"fully insured\". The business carries workers' compensation only. The new site mentions that once, as the answer to \"Are you insured?\" on the questions page, and nowhere else."),
        ("Photos", "All but three photos now come from the full-size originals. Stock photos from the old site were left out, because the gallery says there are none."),
        ("Old pages left out on purpose", "Long distance moving, the 12 city pages, the 10 blog posts, and furniture and appliance removal. Junk removal has not started yet. Every one of those old addresses now forwards to the closest page that still exists, %d in all." % len(REDIRECTS)),
    ]
    head2 = '<div class="table-scroll"><table><thead><tr><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table></div>'
    return page_head("Launch checklist", "Launch checklist",
                     "Everything that has to happen before this site replaces the old one. This page is not part of the public site.") + """
<section class="section"><div class="wrap stack-lg">
  <div class="stack"><h2>Open yellow notes (%d)</h2>
  <p>These are drafts written for Jared to review. The live build will not run until each one is approved or changed.</p>
  <div class="table-scroll"><table><thead><tr><th>Question</th><th>Page</th></tr></thead><tbody>%s</tbody></table></div></div>
  <div class="stack"><h2>Taken from Jared's HireAHelper listing</h2><p>These came from his own public listing, not from him directly. Have him confirm each one still holds.</p>%s</div>
  <div class="stack"><h2>Answered on October 8</h2>%s</div>
  <div class="stack"><h2>Still to come</h2>%s</div>
  <div class="stack"><h2>The domain</h2>%s</div>
  <div class="stack"><h2>Keeping it safe</h2>%s</div>
  <div class="stack"><h2>Before it goes live</h2>%s</div>
  <div class="stack"><h2>Choices already made</h2>%s</div>
</div></section>""" % (len(NOTES), confirm, head2 % ("Fact", "Where it came from", rows(listing)),
                         head2 % ("Question", "What the site says now", rows(answered)),
                         head2 % ("Item", "Detail", rows(ask)),
                         head2 % ("Step", "Why", rows(domain)), head2 % ("Step", "Why", rows(safety)),
                         head2 % ("Step", "Why", rows(launch)), head2 % ("Choice", "Detail", rows(choices)))


# ------------------------------------------------------------------ shell
def header(slug):
    def links():
        return "".join('<a href="%s"%s>%s</a>' % (url(s), ' aria-current="page"' if s == slug else "", label) for s, label in NAV)
    cur = ' aria-current="page"' if slug == "contact" else ""
    preview = ('<div class="preview-bar"><div class="wrap">Preview build. Yellow notes are questions for Jared and come out before launch. '
               '<a href="%s">See the launch checklist</a>.</div></div>' % url("launch-checklist")) if PREVIEW else ""
    return preview + """<a class="skip" href="#main">Skip to content</a>
<header class="bar">
  <div class="wrap">
    <a class="brand" href="%s">%s</a>
    <nav class="nav" aria-label="Main">%s</nav>
    <a class="bar-cta" href="%s"%s>Free estimate</a>
    <a class="bar-phone" href="%s"><span>Call or text</span><b>%s</b></a>
    <details class="menu"><summary>Menu</summary><nav class="menu-panel" aria-label="Main, mobile">%s<a href="%s"%s>Free estimate</a></nav></details>
  </div>
</header>""" % (url("index"), LOGO % "", links(), url("contact"), cur, SITE["tel"], SITE["phone"], links(), url("contact"), cur)


def footer():
    f = """<footer class="foot">
  <div class="wrap">
    <div class="foot-grid">
      <div>
        %s
        <p>Movers in Wilmington, NC since October 2021. Local moves, loading and unloading help, and heavy items, by a crew of UNC Wilmington students.</p>
      </div>
      <div>
        <h2>Services</h2>
        <ul>
          <li><a href="[[url:moving-help]]">Loading and unloading help</a></li>
          <li><a href="[[url:local-moving]]">Local moving</a></li>
          <li><a href="[[url:heavy-items]]">Safes, pianos and hot tubs</a></li>
          <li><a href="[[url:contact]]">Free estimate</a></li>
        </ul>
      </div>
      <div>
        <h2>Company</h2>
        <ul>
          <li><a href="[[url:about]]">About the crew</a></li>
          <li><a href="[[url:reviews]]">Reviews</a></li>
          <li><a href="[[url:gallery]]">Photos</a></li>
          <li><a href="[[url:service-area]]">Service area</a></li>
          <li><a href="[[url:faq]]">Questions</a></li>
        </ul>
      </div>
      <div>
        <h2>Contact</h2>
        <ul>
          <li><a href="[[tel]]">[[phone]]</a></li>
          <li><a href="mailto:[[email]]">[[email]]</a></li>
          <li>[[hours]]</li>
          <li>Wilmington, NC 28403</li>
          <li>%s</li>
          <li>%s, %s, %s</li>
        </ul>
      </div>
    </div>
    <div class="foot-base"><span>&copy; 2026 [[legal]]. <a href="[[url:privacy]]">Privacy</a> and <a href="[[url:terms]]">terms</a>.</span><span>Site by %s</span></div>
  </div>
</footer>
<nav class="callbar" aria-label="Quick contact"><a href="[[tel]]">Call [[phone]]</a><a href="[[url:contact]]">Free estimate</a></nav>""" % (
        LOGO % ' loading="lazy"', ext("[[google]]", "Review us on Google"), ext(SITE["facebook"], "Facebook"), ext(SITE["youtube"], "YouTube"),
        ext(SITE["pinterest"], "Pinterest"), ext("https://zanmediagroup.com", "Zan Media Group"))
    return f


def business_ld():
    towns = ["Wilmington", "Carolina Beach", "Kure Beach", "Wrightsville Beach", "Castle Hayne", "Leland", "Southport",
             "Oak Island", "Boiling Spring Lakes", "Winnabow", "Bolivia", "Hampstead", "Surf City", "Burgaw", "Rocky Point",
             "Jacksonville", "Holly Ridge", "Whiteville", "Lake Waccamaw"]
    return {"@context": "https://schema.org", "@type": "MovingCompany", "@id": SITE["domain"] + "/#business",
            "name": SITE["name"], "legalName": SITE["legal"], "url": SITE["domain"] + "/",
            "telephone": SITE["tel_schema"], "email": SITE["email"],
            "image": SITE["domain"] + "/img/crew-tailgate.jpg", "logo": SITE["domain"] + "/img/logo.png",
            "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Moving services", "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "url": canonical(s)}}
                for s, n in (("moving-help", "Loading and unloading help"), ("local-moving", "Local moving"),
                             ("heavy-items", "Gun safe, upright piano, hot tub and pool table moving"))]},
            "description": "Wilmington, NC moving company for local moves, hourly loading and unloading help, and piano, gun safe, hot tub and pool table moving, with a crew of UNC Wilmington students.",            "foundingDate": "2021-10", "founder": {"@type": "Person", "name": "Jared Mazzola", "jobTitle": "Founder",
                                              "image": SITE["domain"] + "/img/jared-800.webp"},
            "address": {"@type": "PostalAddress", "addressLocality": "Wilmington", "addressRegion": "NC",
                        "postalCode": "28403", "addressCountry": "US"},
            "areaServed": [{"@type": "City", "name": t + ", NC"} for t in towns],
            "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                           "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                           "opens": "08:00", "closes": "19:00"}],
            "sameAs": [SITE["google"], SITE["facebook"], SITE["youtube"], SITE["pinterest"]]}


def csp():
    """Content security policy. GitHub Pages cannot send headers, so this ships as a meta tag."""
    script, connect, img, form = ["'self'"], ["'self'"], ["'self'", "data:"], ["'self'"]
    if SITE["form_action"]:
        o = urlparse(SITE["form_action"])
        origin = "%s://%s" % (o.scheme, o.netloc)
        connect.append(origin); form.append(origin)
    if SITE["ga_id"]:
        script.append("https://www.googletagmanager.com")
        connect += ["https://www.google-analytics.com", "https://*.google-analytics.com", "https://*.analytics.google.com"]
        img += ["https://www.google-analytics.com", "https://www.googletagmanager.com"]
    if SITE["pixel_id"]:
        script.append("https://connect.facebook.net")
        connect.append("https://www.facebook.com")
        img.append("https://www.facebook.com")
    parts = ["default-src 'self'", "script-src " + " ".join(script), "style-src 'self'", "img-src " + " ".join(img),
             "font-src 'self'", "connect-src " + " ".join(connect), "form-action " + " ".join(form),
             "base-uri 'self'", "object-src 'none'", "frame-src 'none'", "upgrade-insecure-requests"]
    return "; ".join(parts)


def ld_tag(data):
    # "</" can never appear inside a script block, so escape it.
    return '<script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def head(p):
    slug, title, desc = p["slug"], html.escape(p["title"]), html.escape(p["desc"], quote=True)
    robots = '<meta name="robots" content="noindex">' if (PREVIEW or not p["index"]) else ""
    lds = []
    if slug == "index":
        lds.append(business_ld())
        lds.append({"@context": "https://schema.org", "@type": "WebSite", "name": "Express Movers",
                    "url": SITE["domain"] + "/", "publisher": {"@id": SITE["domain"] + "/#business"}})
    if p["crumb"]:
        trail = [("Home", canonical("index"))]
        if p.get("parent"):
            trail.append((p["parent"][1], canonical(p["parent"][0])))
        trail.append((p["crumb"], canonical(slug)))
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(trail)]})
    lds += p["extra_ld"]
    lines = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        "" if PREVIEW else '<meta http-equiv="Content-Security-Policy" content="%s">' % csp(),
        '<meta name="referrer" content="strict-origin-when-cross-origin">',
        "<title>%s</title>" % title,
        '<meta name="description" content="%s">' % desc,
        robots,
        '<link rel="canonical" href="%s">' % canonical(slug),
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Express Movers">',
        '<meta property="og:title" content="%s">' % title,
        '<meta property="og:description" content="%s">' % desc,
        '<meta property="og:url" content="%s">' % canonical(slug),
        '<meta property="og:image" content="%s/og-image.jpg">' % SITE["domain"],
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="theme-color" content="#1d1f1c">',
        '<link rel="icon" href="%s" type="image/svg+xml">' % asset("favicon.svg"),
        '<link rel="apple-touch-icon" href="%s">' % asset("apple-touch-icon.png"),
        "" if PREVIEW else '<link rel="preload" href="/fonts/bricolage-grotesque.woff2" as="font" type="font/woff2" crossorigin>',
        "" if PREVIEW else '<link rel="preload" href="/fonts/hanken-grotesk.woff2" as="font" type="font/woff2" crossorigin>',
        '<link rel="stylesheet" href="%s">' % asset("styles.css", versioned=not PREVIEW),
    ] + [ld_tag(d) for d in lds] + [
        '<script src="%s" defer></script>' % asset("site.js", versioned=not PREVIEW),
    ]
    return "\n".join(l for l in lines if l)


def html_attrs(p):
    a = ' lang="en"'
    if SITE["ga_id"]:
        a += ' data-ga="%s"' % html.escape(SITE["ga_id"], quote=True)
    if SITE["pixel_id"]:
        a += ' data-pixel="%s"' % html.escape(SITE["pixel_id"], quote=True)
    if p["lead"]:
        a += " data-lead"
    return a


def document(p, body_html):
    return "<!doctype html>\n<html%s>\n<head>\n%s\n</head>\n<body>\n%s\n<main id=\"main\">%s</main>\n%s\n</body>\n</html>\n" % (
        html_attrs(p), head(p), header(p["slug"]), body_html, render(footer(), p["slug"]))


def write(rel, content, binary=False):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"})) as f:
        f.write(content)


def redirect_page(target_slug):
    dest = canonical(target_slug)
    path = "/" if target_slug == "index" else "/" + target_slug
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>This page has moved | Express Movers</title>\n'
            '<meta name="robots" content="noindex">\n<link rel="canonical" href="%s">\n'
            '<meta http-equiv="refresh" content="0; url=%s">\n</head>\n<body>\n<p>This page has moved. <a href="%s">Continue to Express Movers</a>.</p>\n</body>\n</html>\n'
            % (dest, path, path))


# ------------------------------------------------------------------ build
def main():
    if MODE not in ("preview", "production"):
        sys.exit(__doc__)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    built = []
    for p in PAGES:
        body = render(p["body"], p["slug"])
        built.append((p, body))

    if not PREVIEW and NOTES and not ALLOW_NOTES:
        sys.exit("Not built. %d note(s) still need Jared:\n%s\nRun with --allow-notes for a dry run."
                 % (len(NOTES), "\n".join("  [%s] %s" % n for n in NOTES)))

    for p, body in built:
        write(p["slug"] + ".html", document(p, body))

    if PREVIEW:
        p = dict(slug="launch-checklist", title="Launch checklist | Express Movers", desc="Launch checklist.",
                 crumb=None, index=False, extra_ld=[], lead=False, parent=None)
        write("launch-checklist.html", document(p, render(checklist_body(), "launch-checklist")))

    # assets
    css = open(os.path.join(SRC, "styles.css"), encoding="utf-8").read()
    if PREVIEW:
        # The preview host only loads fonts that are embedded in the stylesheet.
        def embed(m):
            data = open(os.path.join(SRC, "fonts", m.group(1)), "rb").read()
            return 'url("data:font/woff2;base64,%s")' % base64.b64encode(data).decode()
        css = re.sub(r'url\("fonts/([^"]+)"\)', embed, css)
    else:
        shutil.copytree(os.path.join(SRC, "fonts"), os.path.join(OUT, "fonts"))
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        css = re.sub(r"\s+", " ", css)
        css = re.sub(r"\s*([{};,>])\s*", r"\1", css).replace(";}", "}").replace(": ", ":").strip()
    write("styles.css", css)
    shutil.copy(os.path.join(SRC, "site.js"), os.path.join(OUT, "site.js"))
    shutil.copytree(os.path.join(SRC, "img"), os.path.join(OUT, "img"), ignore=shutil.ignore_patterns("manifest.json"))
    for name in ("favicon.svg", "apple-touch-icon.png", "og-image.jpg"):
        shutil.copy(os.path.join(SRC, name), os.path.join(OUT, name))

    if not PREVIEW:
        for old, target in REDIRECTS.items():
            write(old + ".html", redirect_page(target))
        write("CNAME", SITE["host"] + "\n")
        write(".nojekyll", "")
        write("robots.txt", "User-agent: *\nAllow: /\n\n" + "".join(
            "User-agent: %s\nAllow: /\n\n" % b for b in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot", "Google-Extended"))
              + "Sitemap: %s/sitemap.xml\n" % SITE["domain"])
        urls = "".join("  <url><loc>%s</loc><lastmod>2026-10-08</lastmod></url>\n" % canonical(p["slug"])
                       for p in PAGES if p["index"] and p["in_sitemap"])
        write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % urls)
        write(".well-known/security.txt",
              "Contact: mailto:%s\nExpires: 2027-10-08T00:00:00.000Z\nPreferred-Languages: en\nCanonical: %s/.well-known/security.txt\n"
              % (SITE["security_contact"], SITE["domain"]))
        write("llms.txt", LLMS)

    print("%s build: %d pages, %d open note(s) -> %s" % (MODE, len(built) + (1 if PREVIEW else 0), len(NOTES), OUT))
    for n in NOTES:
        print("  note [%s] %s" % n)


LLMS = """# Express Movers

> Movers in Wilmington, NC since October 2021. Local moves, hourly loading and unloading help, and heavy item moving, by a crew of UNC Wilmington students.

## Services
- Loading and unloading help for rental trucks, trailers, storage units and portable containers (a load only, an unload only, or both)
- Local moves for apartments, houses and offices, done in one trip on the same day
- Heavy items for an added fee: gun safes, upright pianos (no grand pianos), hot tubs and pool tables
- Included at no extra charge: hand trucks, dollies with straps, hand tools, and wrapping furniture in the customer's blankets
- Not offered: packing, boxes, long distance moves

## Facts
- Legal name: Express Movers LLC. Founder: Jared Mazzola, who trains every crew member. Started October 2021 while he was a UNCW student. Crew: more than 15 UNC Wilmington students.
- Track record: more than 700 moves since October 2021. 4.9 stars on Google (October 2026)
- How to book: directly with Express Movers by phone or text at (704) 999-3714, or the estimate form at https://www.expressmoversilm.com/contact
- Phone: (704) 999-3714. Email: expressmovers.go@gmail.com
- Hours: every day, 8am to 7pm
- Pricing: by the hour for the crew, with a minimum of two movers for two hours. Free estimates. No deposit to book.
- Same-day jobs: yes, by phone
- Replies: same day for requests between 8am and 7pm, next day for requests sent later
- Payment: cash, Venmo, or invoice

## Where
Based in Wilmington, NC 28403. Travels up to about an hour and ten minutes: Carolina Beach, Kure Beach, Wrightsville Beach, Castle Hayne, Leland, Southport, Oak Island, Hampstead, Surf City, Burgaw, Jacksonville, Holly Ridge, Whiteville and nearby towns. Jobs outside Wilmington may carry a travel fee.

## Pages
- https://www.expressmoversilm.com/moving-help
- https://www.expressmoversilm.com/local-moving
- https://www.expressmoversilm.com/heavy-items
- https://www.expressmoversilm.com/service-area
- https://www.expressmoversilm.com/reviews
- https://www.expressmoversilm.com/faq
- https://www.expressmoversilm.com/contact
"""

if __name__ == "__main__":
    main()
