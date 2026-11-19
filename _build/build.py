#!/usr/bin/env python3
"""Baut die Nexora-Seiten aus gemeinsamen Bausteinen (Header, Footer, Statistik)."""
import pathlib, sys, re, json, hashlib, base64, unicodedata, html as _html
from urllib.parse import urlsplit

# Ausgabeordner: erstes Argument, sonst der Ordner über _build/ (also die Website selbst)
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
OUT.mkdir(parents=True, exist_ok=True)
# "local": Schriften liegen im Ordner fonts/ (DSGVO-freundlich, für die echte Website)
# "google": Schriften von Google Fonts (nur für die Vorschau)
FONT_MODE = sys.argv[2] if len(sys.argv) > 2 else "local"
FONTS_LOCAL = '''<link rel="preload" href="fonts/sora-latin-4fa0aa.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/inter-latin-567244.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="fonts/fonts.css">'''
FONTS_GOOGLE = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">'''

NAV = [("index.html", "Start"), ("leistungen.html", "Leistungen"), ("ueber-uns.html", "Über uns"), ("karriere.html", "Karriere"), ("kontakt.html", "Kontakt")]

# E-Mail-Adressen (Postfach bei Strato, Domain infonexora.de)
INFO_MAIL = "info@infonexora.de"      # allgemeiner Kontakt: Footer, Impressum, Kontaktformular
CAREER_MAIL = "info@infonexora.de"    # Bewerbungen (auch als Ausweichadresse angezeigt). Eigene Adresse wie karriere@ erst eintragen, wenn sie bei Strato existiert

# Adresse der fertigen Website, z. B. "https://www.nexora.de" (ohne / am Ende).
# Leer lassen, solange die Domain nicht feststeht. Gesetzt entstehen daraus Canonical-Links, sitemap.xml und absolute Vorschaubild-Links.
# Die jeweils andere Schreibweise (mit oder ohne www) leitet Vercel per vercel.json hierher um.
# nexora-webstudio.dev: bei Vercel gekauft und mit dem Projekt verbunden (Lennos Wahl vom 19.11.2026)
SITE_URL = "https://nexora-webstudio.dev"

# Firmendaten für Impressum und Datenschutz. Leere Felder erscheinen im Testmodus als markierter Platzhalter
# und werden live einfach weggelassen (Lenno, 19.11.2026: Adresse, HRB und USt-IdNr. vorerst weglassen).
# Nexora ist ein Angebot der Baldwin Bell Green GmbH (Lenno, 19.11.2026).
FIRMA = "Baldwin Bell Green GmbH"
GESCHAEFTSFUEHRER = "Linus Schoeller"
STRASSE = ""            # z. B. "Musterstraße 1"
PLZ_ORT = ""            # z. B. "10115 Berlin"
TELEFON = ""            # z. B. "+49 172 4358302"
REGISTERGERICHT = ""    # z. B. "Amtsgericht Berlin (Charlottenburg)"
HRB = ""                # z. B. "HRB 123456 B"
UST_ID = ""             # z. B. "DE123456789", leer lassen, falls es keine gibt (dann entfällt die Zeile nach dem Ausfüllen)
UST_ID_OFFEN = True     # True, solange noch nicht geklärt ist, ob es eine USt-IdNr. gibt

# Beispielinhalte: True zeigt die Beispiel-Kundenstimmen und die noch unbelegten Zahlen (14 Tage, 99,9 %, 4,9/5).
# False blendet die Kundenstimmen aus und zeigt im Zahlenbereich stattdessen feste Angebotsdaten.
BEISPIELE = False   # seit 19.11.2026 ausgeblendet (Lennos Wahl beim Livegang)

# Testmodus: Solange LIVE = False ist, nehmen Suchmaschinen die Seite nicht auf (noindex), z. B. den Testlink von Vercel.
# LIVE = True: für Google freigegeben, mit Canonical-Links, sitemap.xml und Sitemap-Zeile in robots.txt (seit 19.11.2026).
LIVE = True

# Versand der Formulare: "vercel" (Funktionen api/bewerbung.js und api/anfrage.js über SMTP)
# oder "php" (bewerbung.php und anfrage.php für klassischen Webspace)
FORM_BACKEND = "vercel"

# Antwortzeit, die Kontaktseite und Eingangsbestätigung versprechen
ANTWORTZEIT = "in der Regel innerhalb eines Werktags"

# WhatsApp Business: Nummer im internationalen Format, nur Ziffern (ohne +, Leerzeichen oder führende 0)
WHATSAPP_NUMBER = "491724358302"
WHATSAPP_TEXT = "Hallo Nexora, ich interessiere mich für eine Website."
from urllib.parse import quote as _quote
WA_HREF = f"https://wa.me/{WHATSAPP_NUMBER}?text={_quote(WHATSAPP_TEXT)}"
WA_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>')
WA_ATTRS = f'href="{WA_HREF}" target="_blank" rel="noopener"'
WHATSAPP_ANZEIGE = "+49 172 4358302"   # so erscheint die Nummer im Impressum
WA_FLOAT = f'<a class="wa-float" {WA_ATTRS} aria-label="Nexora per WhatsApp schreiben"><span class="wa-ic">{WA_SVG}</span><span class="wa-txt">WhatsApp</span></a>\n'

ARR = '<span class="arr" aria-hidden="true">→</span>'

ICONS = {
    "server": '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4"/>',
    "archive": '<rect x="3" y="4" width="18" height="5" rx="1.5"/><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4"/>',
    "edit": '<path d="M4 20h4L19 9l-4-4L4 16v4zM14 6l4 4"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>',
    "upload": '<path d="M12 15V4.5M7.5 9 12 4.5 16.5 9"/><path d="M4.5 14.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M4 7.5l8 6 8-6"/>',
}
def icon(name):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


# Kleines Skript im <head>: markiert, dass JavaScript läuft, und zeigt den Vorhang nur nach einem Klick auf einen internen Link
# (normaler Seitenaufruf, der von einer Seite derselben Website kommt). Es speichert nichts im Browser.
# Sein Hash steht in der Content-Security-Policy (vercel.json) und wird beim Bauen automatisch berechnet.
HEAD_JS = ('(function(c){c.remove("no-js");c.add("js");try{var n=performance.getEntriesByType("navigation")[0];'
           'if(n&&n.type==="navigate"&&document.referrer.indexOf(location.origin+"/")===0&&!matchMedia("(prefers-reduced-motion: reduce)").matches){'
           'c.add("entering");setTimeout(function(){c.remove("entering")},2500)}}catch(e){}})(document.documentElement.classList);')
HEAD_JS_HASH = "sha256-" + base64.b64encode(hashlib.sha256(HEAD_JS.encode("utf-8")).digest()).decode()

def head(title, desc, path="", extra_class="", base=False, noindex=False):
    t, d = _html.escape(title), _html.escape(desc)
    img = f"{SITE_URL}/assets/og-image.jpg" if SITE_URL else "assets/og-image.jpg"
    lines = ['<meta charset="utf-8">']
    if base:
        lines.append('<base href="/">')   # 404-Seite: Pfade gelten ab der Startseite, egal unter welcher Adresse sie erscheint
    lines += ['<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">', f'<title>{t}</title>']
    if FONT_MODE == "google":
        lines.append('<meta name="claude:viewport-fit-sides" content="cover">')   # nur für die Vorschau
    lines.append(f'<meta name="description" content="{d}">')
    if noindex or not LIVE:
        lines.append('<meta name="robots" content="noindex">')
    elif SITE_URL:
        lines += [f'<link rel="canonical" href="{SITE_URL}/{path}">', f'<meta property="og:url" content="{SITE_URL}/{path}">']
    lines += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Nexora">',
        '<meta property="og:locale" content="de_DE">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:image" content="{img}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Nexora Webagentur: Websites, die überzeugen.">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="theme-color" content="#0F0C22">',
        '<link rel="icon" href="favicon.ico" sizes="32x32">',
        '<link rel="icon" type="image/png" sizes="96x96" href="assets/favicon-96.png">',
        '<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">',
        FONTS_LOCAL if FONT_MODE == "local" else FONTS_GOOGLE,
        '<link rel="stylesheet" href="styles.css">',
        f'<script>{HEAD_JS}</script>',
    ]
    nl = "\n"
    return f'<!doctype html>\n<html lang="de" class="no-js{extra_class}">\n<head>\n{nl.join(lines)}\n</head>\n<body>\n'


def header(active, cta_href="termin.html"):
    cur = ' aria-current="page"'
    links = "\n      ".join(f'<a href="{h}"{cur if h == active else ""}>{t}</a>' for h, t in NAV)
    mlinks = "\n    ".join(f'<a href="{h}"{cur if h == active else ""}>{t}</a>' for h, t in NAV)
    return f'''<a class="skip" href="#main">Zum Inhalt springen</a>
<div class="curtain" aria-hidden="true"><img src="assets/logo-mark-144.png" alt="" width="72" height="72" fetchpriority="low"></div>
<div class="progress" aria-hidden="true"></div>
<header class="site-head">
  <div class="wrap">
    <a class="brand" href="index.html" aria-label="Nexora Startseite"><img src="assets/logo-lockup-80.png" srcset="assets/logo-lockup-80.png 357w, assets/logo-lockup-120.png 536w, assets/logo-lockup.png 781w" sizes="(max-width: 600px) 152px, 178px" alt="Nexora" width="179" height="40" fetchpriority="high"></a>
    <nav class="nav" aria-label="Hauptnavigation">
      {links}
    </nav>
    <a class="btn btn--grad btn--sm head-cta magnetic" href="{cta_href}">Beratungstermin buchen {ARR}</a>
    <button class="menu-btn" id="menuBtn" type="button" aria-label="Menü öffnen" aria-expanded="false" aria-controls="mobileNav"><span></span></button>
  </div>
  <nav class="mobile-nav" id="mobileNav" aria-label="Mobile Navigation">
    {mlinks}
    <a class="btn btn--grad" href="{cta_href}">Beratungstermin buchen {ARR}</a>
  </nav>
</header>
'''


FOOTER = f'''<footer class="site-foot">
  <div class="wrap">
    <div class="foot-top">
      <div>
        <img src="assets/logo-lockup-white-88.png" srcset="assets/logo-lockup-white-88.png 393w, assets/logo-lockup-white-132.png 589w, assets/logo-lockup-white.png 781w" sizes="196px" alt="Nexora" width="196" height="44" loading="lazy">
        <p class="foot-claim">Your Vision, Our Code. Websites für Unternehmen, gebaut, gehostet und betreut aus einer Hand.</p>
      </div>
      <div><h2>Leistungen</h2><ul><li><a href="leistungen.html#kaufen">Website kaufen</a></li><li><a href="leistungen.html#mieten">Website mieten</a></li><li><a href="leistungen.html#betreuung">Website-Betreuung</a></li><li><a href="leistungen.html#vergleich">Vergleich</a></li></ul></div>
      <div><h2>Nexora</h2><ul><li><a href="ueber-uns.html">Über uns</a></li><li><a href="ueber-uns.html#team">Unser Team</a></li><li><a href="karriere.html">Karriere</a></li><li><a href="termin.html">Beratungstermin</a></li></ul></div>
      <div><h2>Kontakt</h2><ul><li><a href="kontakt.html">Kontaktformular</a></li><li><a href="mailto:{INFO_MAIL}">{INFO_MAIL}</a></li><li><a {WA_ATTRS}>WhatsApp</a></li><li><a href="impressum.html">Impressum</a></li><li><a href="datenschutz.html">Datenschutz</a></li></ul></div>
    </div>
    <div class="foot-big" aria-hidden="true"></div>
    <div class="foot-bottom"><span>© <span data-year>2026</span> Nexora. Alle Rechte vorbehalten.</span><span>Webdesign · Entwicklung · Hosting · Betreuung</span></div>
  </div>
</footer>
<script src="main.js"></script>
</body>
</html>
'''

# Platzhalter-Zahlen außer "1.000+ Kunden": vor Livegang durch echte Werte ersetzen.
if BEISPIELE:
    STAT_LEDE = "Hinter jeder Zahl steht ein Unternehmen, das heute mit seiner Website mehr erreicht als vorher."
    STAT_TILES = (
        '<div class="stat" data-obs><div class="stat-num"><span data-count="14">14</span><span class="u"> Tage</span></div><p>im Schnitt vom Erstgespräch bis zum Livegang</p><div class="bar"><i style="--w:62%"></i></div></div>\n'
        '      <div class="stat" data-obs><div class="stat-num"><span data-count="99.9" data-decimals="1" data-from="90">99,9</span><span class="u"> %</span></div><p>Verfügbarkeit unserer Server im Jahresmittel</p><div class="bar"><i style="--w:99.9%"></i></div></div>\n'
        '      <div class="stat" data-obs><div class="stat-num"><span data-count="4.9" data-decimals="1">4,9</span><span class="u">/5</span></div><p>durchschnittliche Bewertung unserer Kunden</p><div class="bar"><i style="--w:98%"></i></div></div>')
else:
    # feste Angebotsdaten statt unbelegter Werte
    STAT_LEDE = "Klare Preise, schnelle Antworten und feste Ansprechpersonen, die Ihre Website betreuen."
    STAT_TILES = (
        '<div class="stat" data-obs><div class="stat-num"><span class="u">ab </span><span data-count="150">150</span><span class="u"> €</span></div><p>im Monat für Ihre Website zur Miete, inkl.&nbsp;Hosting, zzgl.&nbsp;MwSt.</p><div class="bar"><i style="--w:60%"></i></div></div>\n'
        '      <div class="stat" data-obs><div class="stat-num"><span data-count="30">30</span><span class="u"> Min.</span></div><p>kostenlose und unverbindliche Erstberatung</p><div class="bar"><i style="--w:50%"></i></div></div>\n'
        '      <div class="stat" data-obs><div class="stat-num"><span>1</span><span class="u"> Werktag</span></div><p>in der Regel bis zur Antwort auf Ihre Anfrage</p><div class="bar"><i style="--w:85%"></i></div></div>')

STATS_CLS = "" if BEISPIELE else " stats--lang"   # längere Einheiten (ab 150 €, 1 Werktag): Schrift auf großen Bildschirmen etwas kleiner
STAT_HINWEIS = '<!-- Hinweis: Werte außer "1.000+ Kunden" sind Platzhalter und müssen vor dem Livegang geprüft werden. -->' if BEISPIELE else ""
UPTIME_ROW = "<span>letzte 30 Tage</span><span>99,9 % online</span>" if BEISPIELE else "<span>SSL · Backup · Monitoring</span><span>inklusive</span>"
# Performance-Anzeigen (Hero-Badge und Leistungskarte): Lenno will sie wie gestaltet, PageSpeed 98 mobil (19.11.2026).
# PAGESPEED_MESSWERTE = True zeigt stattdessen die gemessenen Lighthouse-Werte dieser Website am Desktop (100, LCP 0,5 s, CLS 0, TBT 0 ms).
PAGESPEED_MESSWERTE = False
if not PAGESPEED_MESSWERTE:
    PS_WERT, PS_ART, PS_STYLE, PS_VITALS, PS_SATZ = "98", "mobil", "", ("1,1 s", "0,01", "30 ms"), ""
else:
    PS_WERT, PS_ART, PS_STYLE, PS_VITALS, PS_SATZ = "100", "Desktop", ' style="--ps-off:0;--g-off:0"', ("0,5 s", "0,00", "0 ms"), " So schnell lädt diese Website."
PS_CLASS = ' class="w3"' if len(PS_WERT) > 2 else ""

def stats(title="Zahlen, die für sich sprechen.", eyebrow="Nexora in Zahlen"):
    return f'''<section class="section dark" aria-labelledby="stats-h">
  <div class="wrap">
    <div class="head head--split">
      <div style="display:grid;gap:22px"><span class="eyebrow">{eyebrow}</span><h2 id="stats-h" class="reveal">{title}</h2></div>
      <p class="lede reveal" data-d="1">{STAT_LEDE}</p>
    </div>
    {STAT_HINWEIS}
    <div class="stats{STATS_CLS}">
      <div class="stat" data-obs><div class="stat-num"><span data-count="1000">1.000</span><span class="u">+</span></div><p>zufriedene Kunden aus ganz Deutschland</p><div class="bar"><i style="--w:100%"></i></div></div>
      {STAT_TILES}
    </div>
  </div>
</section>
'''

def cta(title="Ihre Vision.<br>Unser Code.", text="Buchen Sie ein kostenloses Beratungsgespräch. Nach 30 Minuten wissen Sie, was Ihre Website kostet und wann sie online gehen kann."):
    return f'''<section class="section dark">
  <div class="cta-mark" aria-hidden="true"></div>
  <div class="wrap cta">
    <span class="eyebrow">Kostenlose Beratung</span>
    <h2 class="reveal">{title}</h2>
    <p class="lede reveal" data-d="1">{text}</p>
    <div class="hero-actions reveal" data-d="2">
      <a class="btn btn--grad magnetic" href="termin.html">Beratungstermin buchen {ARR}</a>
      <a class="btn btn--light" href="leistungen.html">Preise ansehen</a>
    </div>
  </div>
</section>
'''

def plans(compact=True):
    more = '' if not compact else f'<p class="fine reveal">Alle Preise zzgl. MwSt. Was genau in Ihrem Paket steckt, sehen Sie unter <a href="leistungen.html">Leistungen &amp; Preise</a>.</p>'
    ids = ('', '', '') if compact else (' id="kaufen"', ' id="mieten"', ' id="betreuung"')
    buy_extra = '' if compact else '<li>Kontaktformular und Google Maps</li><li>Hosting auf Wunsch dazubuchbar</li>'
    rent_extra = '' if compact else '<li>Monitoring rund um die Uhr</li><li>Kein großer Betrag zum Start</li>'
    care_extra = '' if compact else '<li>Umzug auf unser Hosting</li><li>Feste Ansprechperson</li>'
    return f'''<div class="plans">
        <article class="plan reveal"{ids[1]}>
          <div class="plan-top"><h3>Website mieten</h3></div>
          <div class="price"><small>ab</small><strong>150 €</strong><small>pro Monat</small></div>
          <p class="plan-note">Alles inklusive: Website, Hosting, Wartung und Änderungen. Sie konzentrieren sich auf Ihr Geschäft.</p>
          <ul class="checks"><li>Design und Entwicklung inklusive</li><li>Hosting, Domain und SSL-Zertifikat</li><li>Updates und Sicherheit</li><li>Tägliche Backups</li><li>Inhaltsänderungen inklusive</li><li>Persönliche Ansprechperson</li>{rent_extra}</ul>
          <a class="btn btn--ghost" href="termin.html">Beratungstermin buchen {ARR}</a>
        </article>
        <article class="plan plan--feat reveal" data-d="1"{ids[0]}>
          <span class="badge">Beliebteste Wahl</span>
          <div class="plan-top"><h3>Website kaufen</h3></div>
          <div class="price"><small>ab</small><strong>1.000 €</strong><small>einmalig</small></div>
          <p class="plan-note">Einmal zahlen, dauerhaft besitzen. Ideal, wenn Sie Ihre Website selbst in der Hand haben möchten.</p>
          <ul class="checks"><li>Individuelles Design</li><li>Optimiert für Handy, Tablet und Desktop</li><li>SEO-Grundeinrichtung</li><li>Impressum und Datenschutz eingebunden</li><li>Übergabe mit persönlicher Einweisung</li>{buy_extra}</ul>
          <a class="btn btn--grad magnetic" href="termin.html">Beratungstermin buchen {ARR}</a>
        </article>
        <article class="plan reveal" data-d="2"{ids[2]}>
          <div class="plan-top"><h3>Website-Betreuung</h3></div>
          <div class="price"><strong class="word">Auf Anfrage</strong></div>
          <p class="plan-note">Sie haben schon eine Website? Wir übernehmen Pflege, Technik und Weiterentwicklung.</p>
          <ul class="checks"><li>Wartung und Updates</li><li>Fehlerbehebung und Sicherheitschecks</li><li>Neue Seiten und Inhalte</li><li>Ladezeit- und SEO-Optimierung</li>{care_extra}</ul>
          <a class="btn btn--ghost" href="kontakt.html?anliegen=betreuung">Anfrage senden {ARR}</a>
        </article>
      </div>
      {more}'''

# Beispielstimmen (Platzhalter), vor Livegang durch echte Bewertungen ersetzen
REVIEWS = [
    ("MK", "Inhaber, Handwerksbetrieb", "Zwei Wochen nach dem ersten Gespräch war unsere Website online. Seitdem kommen deutlich mehr Anfragen rein."),
    ("SB", "Praxisinhaberin", "Das Mietmodell war für uns perfekt. Kein großer Betrag am Anfang und um Technik müssen wir uns nicht kümmern."),
    ("TR", "Gastronom", "Änderungen an der Speisekarte schicke ich per Mail, am nächsten Tag sind sie online."),
    ("LW", "Immobilienmaklerin", "Modern, schnell und genau so, wie wir uns das vorgestellt haben. Die Beratung war ehrlich und klar."),
    ("AH", "Geschäftsführer, Logistik", "Unsere alte Seite war langsam und unsicher. Nexora hat alles übernommen und modernisiert."),
    ("JP", "Fitnessstudio", "Wir werden bei Google jetzt viel besser gefunden. Das merken wir direkt an den Probetrainings."),
    ("NK", "Kanzlei", "Seriös, übersichtlich und datenschutzkonform. Genau das, was wir gebraucht haben."),
    ("DS", "Einzelhandel", "Feste Ansprechperson, schnelle Antworten, faire Preise. Kann ich nur empfehlen."),
]
def review(r, dup=False):
    i, who, txt = r
    hide = ' aria-hidden="true"' if dup else ''
    return f'<figure class="review" style="margin:0"{hide}><span class="stars" role="img" aria-label="5 von 5 Sternen">★★★★★</span><p>„{txt}“</p><footer><i>{i}</i><span>{who}<small>Kunde seit 2024</small></span></footer></figure>'

def reviews():
    if not BEISPIELE:
        return ""   # Beispiel-Kundenstimmen ausgeblendet, bis echte Bewertungen vorliegen
    # zweite Hälfte nur für die Endlos-Animation, für Screenreader ausgeblendet
    a = "".join(review(r) for r in REVIEWS[:4]) + "".join(review(r, True) for r in REVIEWS[:4])
    b = "".join(review(r) for r in REVIEWS[4:]) + "".join(review(r, True) for r in REVIEWS[4:])
    return f'''<section class="section" aria-labelledby="rev-h">
  <div class="wrap">
    <div class="head head--center">
      <span class="eyebrow">Kundenstimmen</span>
      <h2 id="rev-h" class="reveal">Über 1.000 Kunden. Und sie reden darüber.</h2>
    </div>
  </div>
  <!-- Beispielstimmen: vor dem Livegang durch echte Bewertungen ersetzen -->
  <div class="reviews">
    <div class="r-track">{a}</div>
    <div class="r-track rev">{b}</div>
  </div>
</section>
'''

PAGES = []   # für sitemap.xml

def page(name, title, desc, active, body, cta_href="termin.html", **opts):
    wa = "" if name in ("termin.html", "bewerbung.html", "kontakt.html") else WA_FLOAT
    path = "" if name == "index.html" else name
    html = head(title, desc, path, **opts) + header(active, cta_href) + '<main id="main">\n' + body + "</main>\n" + wa + FOOTER
    html = re.sub(r"[ \t]+\n", "\n", html)
    (OUT / name).write_text(html, encoding="utf-8")
    if not opts.get("noindex"):
        PAGES.append(path)


# ================= Team =================
# Profile, gegliedert nach Bereichen (TEAM_GROUPS). "text" ist optional (ein bis zwei Sätze).
# Fotos: quadratisch, Gesicht mittig, mindestens 200 x 200 px, als assets/team/<vorname-nachname>.jpg ablegen
# (z. B. assets/team/linus-schoeller.jpg, Umlaute ohne Punkte). Beim Bauen wird das Foto automatisch erkannt.
# Ohne Foto erscheinen die Initialen.
TEAM_GROUPS = [("lead", "Geschäftsführung und Kundenbetreuung"), ("dev", "Entwicklung und Design"), ("marketing", "Marketing")]
TEAM = [
    {"group": "lead", "name": "Linus Schoeller", "role": "Founder & Managing Director",
     "text": "Kundenakquise, strategische Unternehmensentwicklung, Betreuung von Großkunden und Projektverhandlungen.",
     "skills": ["Business Development", "Client Relations", "Project Acquisition", "Strategic Partnerships"]},
    {"group": "lead", "name": "Maël Valtieri", "role": "Senior Client Relations Manager",
     "text": "Internationale Kundenbetreuung, Koordination zwischen Kunden und Entwicklern, Projektplanung und langfristige Kundenbindung.",
     "skills": ["Key Account Management", "CRM", "Client Communication", "Project Coordination", "Customer Success"]},
    {"group": "dev", "name": "Cassian Veyr", "role": "Senior Full-Stack Developer", "skills": ["React", "Next.js", "Node.js", "TypeScript", "PostgreSQL"]},
    {"group": "dev", "name": "Elian Vossler", "role": "Senior Frontend Developer", "skills": ["React", "GSAP", "Tailwind CSS", "Web Animations"]},
    {"group": "dev", "name": "Kaelan Rhys", "role": "Mobile App Developer", "skills": ["Flutter", "Swift", "Kotlin", "React Native"]},
    {"group": "dev", "name": "Soren Albrecht", "role": "UI/UX & Frontend Developer", "skills": ["Figma", "Framer", "React", "Design Systems"]},
    {"group": "dev", "name": "Darian Kessler", "role": "Backend Engineer", "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Redis"]},
    {"group": "dev", "name": "Lucien Valcourt", "role": "Shopify & E-Commerce Developer", "skills": ["Shopify Liquid", "Hydrogen", "JavaScript", "React"]},
    {"group": "dev", "name": "Leander Falkenrath", "role": "Full-Stack Developer", "skills": ["Next.js", "React", "MongoDB", "Node.js", "TypeScript"]},
    {"group": "dev", "name": "Aurelian Moreau", "role": "Creative & 3D Web Developer", "skills": ["Three.js", "WebGL", "Blender", "GSAP"]},
    {"group": "dev", "name": "Kian Sorell", "role": "Mobile & Full-Stack Developer", "skills": ["React Native", "Flutter", "Firebase", "Supabase"]},
    {"group": "dev", "name": "Nerian Falk", "role": "Web Performance Engineer", "skills": ["Next.js", "Astro", "Technical SEO", "Core Web Vitals"]},
    {"group": "dev", "name": "Evren Callister", "role": "AI & Automation Developer", "skills": ["Python", "OpenAI API", "LangChain", "n8n"]},
    {"group": "dev", "name": "Tavian Mercer", "role": "DevOps & Cloud Engineer", "skills": ["AWS", "Docker", "Kubernetes", "Terraform"]},
    {"group": "dev", "name": "Caius Ellery", "role": "Senior Software Architect", "skills": ["React", "Python", "Node.js", "PostgreSQL", "AWS"]},
    {"group": "marketing", "name": "Ezra Novaire", "role": "Senior Digital Marketing Strategist",
     "text": "Performance-Kampagnen, Leadgenerierung, datengetriebene Marketingstrategien und Skalierung digitaler Geschäftsmodelle.",
     "skills": ["Google Ads", "Meta Ads", "SEO", "Performance Marketing", "Conversion Optimization", "Analytics"]},
    {"group": "marketing", "name": "Lior Avelin", "role": "Brand & Creative Marketing Specialist",
     "text": "Markenpositionierung, kreative Werbekampagnen, Social-Media-Strategien und Aufbau einer starken digitalen Markenidentität.",
     "skills": ["Brand Strategy", "Social Media Marketing", "Content Creation", "Copywriting", "Creative Direction", "Email Marketing"]},
]
TEAM_HOME = ["Linus Schoeller", "Maël Valtieri", "Caius Ellery", "Ezra Novaire"]   # Auswahl für die Startseite (ohne Beschreibungstext)
TEAM_WIDE = ("lead", "marketing")   # Bereiche mit Beschreibungstexten: zwei breite Karten pro Zeile

def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

_TEAM_DIR = pathlib.Path(__file__).resolve().parent.parent / "assets" / "team"
for _m in TEAM:
    for _ext in ("jpg", "webp", "png"):
        if not _m.get("photo") and (_TEAM_DIR / f"{slug(_m['name'])}.{_ext}").is_file():
            _m["photo"] = f"assets/team/{slug(_m['name'])}.{_ext}"

def initials(name):
    parts = [p for p in re.split(r"[\s-]+", name) if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

def avatar(m, i):
    if m.get("photo"):
        return f'<img class="avatar" src="{m["photo"]}" alt="" width="112" height="112" loading="lazy">'
    return f'<span class="avatar" data-t="{i % 3}" aria-hidden="true">{initials(m["name"])}</span>'

def member(m, i, level="h4", with_text=True):
    e = _html.escape
    text = f'\n        <p class="member-text">{e(m["text"])}</p>' if with_text and m.get("text") else ""
    skills = "".join(f"<li>{e(x)}</li>" for x in m.get("skills", []))
    skills = f'\n        <ul class="member-skills" aria-label="Schwerpunkte">{skills}</ul>' if skills else ""
    return (f'<article class="member reveal" data-d="{i % 3}">\n'
            f'        <div class="member-top">{avatar(m, i)}<div><{level} class="member-name">{e(m["name"])}</{level}><p class="member-role">{e(m["role"])}</p></div></div>{text}{skills}\n'
            f'      </article>')

def job_card(i):
    # Karte "Verstärkung gesucht" am Ende der Entwicklung, führt zur Stellenanzeige
    return (f'<a class="member member--job reveal" data-d="{i % 3}" href="karriere.html#developer">\n'
            f'        <div class="member-top"><span class="avatar avatar--job" aria-hidden="true">+</span><div><b class="member-name">Verstärkung gesucht</b><p class="member-role">Developer (m/w/d)</p></div></div>\n'
            f'        <p class="member-text">Vollzeit, remote oder vor Ort. Hier ist Platz für ein neues Gesicht.</p>\n'
            f'        <span class="member-more">Zur Stellenanzeige {ARR}</span>\n'
            f'      </a>')

def team_section(home=False):
    if not TEAM:
        return ""
    head = '<div style="display:grid;gap:22px"><span class="eyebrow">Unser Team</span><h2 id="team-h" class="reveal">Die Menschen hinter Nexora.</h2></div>'
    if home:
        featured = [m for n in TEAM_HOME for m in TEAM if m["name"] == n] or TEAM[:4]
        rest = [m for m in TEAM if m not in featured]
        cards = "\n      ".join(member(m, i, "h3", with_text=False) for i, m in enumerate(featured))
        body = f'<div class="members members--home">\n      {cards}\n    </div>'
        stack = "".join(avatar(m, i + 1) for i, m in enumerate(rest[:5]))
        more = f'<span class="avatar avatar--more">+{len(rest) - 5}</span>' if len(rest) > 5 else ""
        foot = (f'<div class="stack" aria-hidden="true">{stack}{more}</div><p>{len(TEAM)} Köpfe aus Entwicklung, Design, Marketing und Kundenbetreuung.</p>'
                f'<a class="btn btn--ghost" href="ueber-uns.html#team">Ganzes Team kennenlernen {ARR}</a>')
        lede = "Feste Ansprechpersonen statt Callcenter. Diese Menschen planen, bauen und betreuen Ihre Website."
        attrs = 'style="padding-top:0" aria-labelledby="team-h"'
    else:
        groups, n = [], 0
        for key, title in TEAM_GROUPS:
            ms = [m for m in TEAM if m.get("group") == key]
            if not ms:
                continue
            cards = [member(m, n + i) for i, m in enumerate(ms)]
            n += len(ms)
            if key == "dev":
                cards.append(job_card(n))
            wide = " members--wide" if key in TEAM_WIDE else ""
            cards = "\n      ".join(cards)
            groups.append(f'<div class="team-group">\n    <h3 class="team-group-h reveal">{_html.escape(title)}<span>{len(ms)}</span></h3>\n'
                          f'    <div class="members{wide}">\n      {cards}\n    </div>\n    </div>')
        body = "\n    ".join(groups)
        foot = f'<p>Wir suchen Verstärkung im Vertrieb und in der Entwicklung.</p><a class="btn btn--ghost" href="karriere.html">Offene Stellen ansehen {ARR}</a>'
        lede = f"Feste Ansprechpersonen statt Callcenter. Lernen Sie die {len(TEAM)} Menschen kennen, die Ihre Website planen, bauen und betreuen."
        attrs = 'style="padding-top:0" id="team" aria-labelledby="team-h"'
    return (f'<section class="section" {attrs}>\n  <div class="wrap">\n    <div class="head head--split">\n      {head}\n'
            f'      <p class="lede reveal" data-d="1">{lede}</p>\n    </div>\n    {body}\n'
            f'    <div class="team-foot reveal">{foot}</div>\n  </div>\n</section>\n')

# ================= Startseite: Design-Karte =================
# Kleine Design-Arbeitsfläche: drei Beispiel-Designs (Handwerk, Praxis, Café) wechseln sich ab,
# ein Cursor wählt dazu im Farbfeld die nächste Farbe. Ablauf in main.js, Gestaltung in styles.css (.studio, .sb-*).
STUDIO_THEMES = [
    {"kicker": "Tischlerei &amp; Innenausbau", "h": "Handwerk, das bleibt.", "btn": "Angebot anfragen", "url": "ihre-tischlerei.de", "font": "Serif, fett", "hex": "#B4621C"},
    {"kicker": "Hausarztpraxis", "h": "Gut betreut.", "btn": "Termin buchen", "url": "ihre-praxis.de", "font": "Inter, halbfett", "hex": "#138A7C"},
    {"kicker": "Café &amp; Frühstück", "h": "Guten Morgen.", "btn": "Tisch reservieren", "url": "ihr-cafe.de", "font": "Sora, fett", "hex": "#FF7A59"},
]
STUDIO_ART = [
    '<svg viewBox="0 0 120 90"><g fill="#B4621C"><rect x="18" y="20" width="70" height="13" rx="3" opacity=".92"/>'
    '<rect x="32" y="39" width="72" height="13" rx="3" opacity=".7"/><rect x="12" y="58" width="76" height="13" rx="3" opacity=".5"/></g></svg>',
    '<svg viewBox="0 0 120 90"><circle cx="60" cy="45" r="30" fill="#fff" opacity=".6"/>'
    '<g fill="#138A7C"><rect x="53" y="27" width="14" height="36" rx="4"/><rect x="42" y="38" width="36" height="14" rx="4"/></g></svg>',
    '<svg viewBox="0 0 120 90"><g class="steam" fill="none" stroke="#FFC2A6" stroke-width="3" stroke-linecap="round">'
    '<path d="M52 18c-4 5 4 9 0 14"/><path d="M64 16c-4 5 4 9 0 14"/></g>'
    '<path d="M38 40h44v10a22 22 0 0 1-44 0z" fill="#FF7A59"/><path d="M82 44h4a8 8 0 0 1 0 16h-6" fill="none" stroke="#FF7A59" stroke-width="4"/>'
    '<rect x="32" y="74" width="56" height="4" rx="2" fill="#FFC2A6" opacity=".45"/></svg>',
]
CURSOR_SVG = ('<svg viewBox="0 0 20 20" width="20" height="20"><path d="M3 2.5v13.4l3.6-3.3 2.6 5.6 2.6-1.2-2.6-5.5h5z" '
              'fill="currentColor" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>')

def _swap(key, cls):
    # gestapelte Varianten, sichtbar ist jeweils die des aktiven Designs
    items = "".join(f"<b>{t[key]}</b>" for t in STUDIO_THEMES)
    return f'<span class="sb-x {cls}">{items}</span>'

def studio_card():
    art = '<span class="sb-x sb-art">' + "".join(f"<span>{svg}</span>" for svg in STUDIO_ART) + "</span>"
    head = '<span class="sb-sel">' + _swap("h", "sb-h") + "</span>"
    desk = ('<div class="sb-frame sb-desk"><span class="sb-label">Desktop · ' + _swap("url", "sb-url") + "</span>"
            '<div class="sb-page"><div class="sb-nav"><i class="sb-logo"></i><span class="sb-links"><i></i><i></i><i></i></span><i class="sb-pill"></i></div>'
            '<div class="sb-hero"><div class="sb-copy">' + _swap("kicker", "sb-kick") + head +
            '<i class="sb-line"></i><i class="sb-line"></i>' + _swap("btn", "sb-btn") + "</div>" + art + "</div></div></div>")
    phone = ('<div class="sb-frame sb-phone"><span class="sb-label">Mobil</span>'
             '<div class="sb-page"><div class="sb-nav"><i class="sb-logo"></i><i class="sb-burger"></i></div>' + art + head +
             '<i class="sb-line"></i>' + _swap("btn", "sb-btn") + "</div></div>")
    dots = "".join("<i></i>" for _ in STUDIO_THEMES)
    panel = ('<div class="sb-panel" aria-hidden="true">'
             '<span class="sb-ph"><span>Farbe</span>' + _swap("hex", "sb-hex") + "</span>"
             f'<span class="sb-sw">{dots}</span>'
             '<span class="sb-ph"><span>Schrift</span></span>'
             '<span class="sb-font"><span class="sb-x sb-aa"><b>Aa</b><b>Aa</b><b>Aa</b></span>' + _swap("font", "sb-fname") + "</span></div>")
    cursor = f'<div class="sb-cursor" aria-hidden="true">{CURSOR_SVG}<span>Design-Team</span></div>'
    return ('<article class="card b-1 reveal studio" data-theme="0">\n'
            '        <span class="k">Design</span>\n'
            '        <h3>Gestaltung, die auffällt</h3>\n'
            '        <p>Kein Baukasten von der Stange. Jede Website wird für Ihr Unternehmen entworfen, klar, modern und auf Ihre Kunden ausgerichtet.</p>\n'
            f'        <div class="sb" aria-hidden="true">{desk}{phone}</div>\n'
            f'        {panel}{cursor}\n'
            '      </article>')

# ================= Startseite =================
# Hero-Bühne: Beispiel-Website eines Handwerksbetriebs im Browserfenster (reine Dekoration, aria-hidden).
# Ablauf in main.js: Ladebalken, die Inhalte erscheinen, im Haus gehen die Lichter an, ein Besucher klickt
# auf "Termin anfragen" und die Meldung "Neue Anfrage" erscheint. Gestaltung in styles.css (.hs-*).
def _hs_svg(paths, cls="hs-i", box="0 0 24 24"):
    return f'<svg class="{cls}" viewBox="{box}" focusable="false">{paths}</svg>'

HS_STAR = '<path d="M12 2.8l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 16.8l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>'
HS_STARS = _hs_svg("".join(f'<g transform="translate({i * 24} 0)">{HS_STAR}</g>' for i in range(5)), "hs-stars", "0 0 120 24")
HS_LOCK = _hs_svg('<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>', "lock")
HS_MARK = _hs_svg('<path d="M4.5 11.2L12 5l7.5 6.2v8.3h-15z"/><path d="M10 19.5v-5h4v5"/>')
HS_ARROW = _hs_svg('<path d="M5 12h13M13 7l5 5-5 5"/>')
HS_SHIELD = _hs_svg('<path d="M12 3l7 3v5.5c0 4.2-3 7.9-7 9-4-1.1-7-4.8-7-9V6z"/><path d="M8.8 12.2l2.2 2.2 4.3-4.4"/>')
# Ring für PageSpeed 98: Umfang 2·π·15 = 94,25, davon 98 % gefüllt
HS_RING = _hs_svg('<circle class="ps-t" cx="18" cy="18" r="15"/><circle class="ps-v" cx="18" cy="18" r="15"/>', "ps-ring", "0 0 36 36")
# Mauszeiger: Pfeil und Hand, die Spitze liegt jeweils auf dem Ursprung von .hs-cursor (siehe CSS)
HS_POINTER = _hs_svg('<path d="M2.5 2.2l14.6 10.4-6.5 1.3 3.8 7.4-2.9 1.4-3.8-7.4-5.2 4.6z"/>', "hs-pt", "0 0 20 24")
HS_HAND = _hs_svg('<path d="M9.6 1.8c1.05 0 1.9.85 1.9 1.9v6.1c.3-.2.7-.3 1.1-.3 1 0 1.8.7 1.9 1.6.3-.2.7-.3 1.1-.3 1 0 1.8.8 1.9 1.7.3-.15.6-.2.9-.2 '
                  '1 0 1.9.85 1.9 1.9v3.6c0 3.9-3 6.9-6.9 6.9h-1.1c-2.3 0-4.4-1.1-5.7-3L3.3 15.4c-.6-.85-.4-2 .45-2.6.85-.6 2-.4 2.6.45l1.35 1.9V3.7'
                  'c0-1.05.85-1.9 1.9-1.9z"/><path class="hs-f" d="M11.5 9.8v3.6M14.5 11.1v2.7M17.5 12.5v2.2"/>', "hs-hand", "0 0 24 26")
HS_HOUSE = (
    '<svg class="hs-art" viewBox="0 0 480 340" preserveAspectRatio="xMidYMid slice" focusable="false"><defs>'
    '<linearGradient id="hs-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4B3BC8"/><stop offset=".42" stop-color="#8E89F3"/>'
    '<stop offset=".72" stop-color="#D8D0FF"/><stop offset="1" stop-color="#FFDCC6"/></linearGradient>'
    '<radialGradient id="hs-sun"><stop offset="0" stop-color="#FFF5DF"/><stop offset=".3" stop-color="#FFDDB0" stop-opacity=".85"/>'
    '<stop offset="1" stop-color="#FFDDB0" stop-opacity="0"/></radialGradient>'
    '<linearGradient id="hs-win" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF1C9"/><stop offset="1" stop-color="#FFB25A"/></linearGradient>'
    '<radialGradient id="hs-spill"><stop offset="0" stop-color="#FFC66F" stop-opacity=".55"/><stop offset="1" stop-color="#FFC66F" stop-opacity="0"/></radialGradient>'
    '<pattern id="hs-wood" width="8" height="10" patternUnits="userSpaceOnUse"><rect width="8" height="10" fill="#8E5834"/><rect width="1.3" height="10" fill="#6C4022"/></pattern>'
    '</defs>'
    '<rect width="480" height="340" fill="url(#hs-sky)"/>'
    # Sterne und Wolken
    '<g fill="#fff"><circle cx="46" cy="34" r="1.3" opacity=".8"/><circle cx="120" cy="58" r="1" opacity=".6"/><circle cx="182" cy="26" r="1.2" opacity=".7"/>'
    '<circle cx="262" cy="48" r="1" opacity=".6"/><circle cx="338" cy="22" r="1.3" opacity=".8"/><circle cx="446" cy="44" r="1" opacity=".6"/></g>'
    '<g fill="#fff" opacity=".22"><ellipse cx="96" cy="104" rx="40" ry="8"/><ellipse cx="110" cy="96" rx="20" ry="10"/><ellipse cx="84" cy="99" rx="13" ry="7"/>'
    '<ellipse cx="330" cy="84" rx="30" ry="6"/><ellipse cx="342" cy="78" rx="14" ry="7"/></g>'
    # tief stehende Sonne, Hügel, Boden
    '<circle cx="402" cy="186" r="92" fill="url(#hs-sun)"/><circle cx="402" cy="186" r="21" fill="#FFF2D6"/>'
    '<path d="M0 226C64 204 132 214 200 206s150-20 280 2v132H0z" fill="#A99EF2" opacity=".75"/>'
    '<path d="M0 250c84-18 170-10 250-16s156-4 230 10v96H0z" fill="#7C6CD8" opacity=".85"/>'
    '<rect y="262" width="480" height="78" fill="#2A2160"/>'
    '<ellipse class="hs-glow" cx="228" cy="268" rx="170" ry="30" fill="url(#hs-spill)"/>'
    # Baum links
    '<rect x="76" y="212" width="6" height="52" rx="2" fill="#17112F"/>'
    '<circle cx="79" cy="194" r="30" fill="#3B2F80"/><circle cx="98" cy="213" r="19" fill="#4A3D99"/><circle cx="60" cy="213" r="17" fill="#33296F"/>'
    # Haus mit Satteldach und Anbau in Holz
    '<path d="M128 264V158l88-54 88 54v106z" fill="#1F1942"/>'
    '<path d="M112 166L216 101l104 65" fill="none" stroke="#0F0C22" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>'
    '<rect x="300" y="192" width="96" height="72" fill="url(#hs-wood)"/>'
    '<rect x="294" y="184" width="108" height="9" rx="1.5" fill="#0F0C22"/>'
    '<g fill="#2E2858"><rect x="146" y="174" width="66" height="62" rx="2"/><rect x="226" y="174" width="62" height="26" rx="2"/>'
    '<rect x="316" y="206" width="64" height="38" rx="2"/><circle cx="216" cy="134" r="11"/></g>'
    '<g fill="url(#hs-win)"><rect class="hs-w w1" x="146" y="174" width="66" height="62" rx="2"/><rect class="hs-w w2" x="226" y="174" width="62" height="26" rx="2"/>'
    '<rect class="hs-w w3" x="316" y="206" width="64" height="38" rx="2"/><circle class="hs-w w4" cx="216" cy="134" r="11"/></g>'
    '<path d="M179 174v62M146 205h66M257 174v26M348 206v38" stroke="#0F0C22" stroke-width="3"/>'
    '<rect x="236" y="212" width="30" height="52" rx="2" fill="#0F0C22"/><circle cx="259" cy="239" r="1.8" fill="#FFC66F"/>'
    '<path d="M238 264h26l32 76h-90z" fill="#3A3079"/>'
    '<g fill="#FFD48F"><circle cx="214" cy="300" r="2.4"/><circle cx="292" cy="300" r="2.4"/></g>'
    '<ellipse cx="420" cy="262" rx="30" ry="14" fill="#3B2F80"/><ellipse cx="447" cy="266" rx="18" ry="10" fill="#4A3D99"/>'
    '</svg>'
)
HS_CARDS = [
    ('<rect x="4" y="3.5" width="13" height="5.5" rx="1.5"/><path d="M17 6.2h2.5v5.3h-8.3v3"/><rect x="9.7" y="14.5" width="3" height="6.5" rx="1"/>',
     "Sanierung", "Bad, Küche, Fenster"),
    ('<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>', "Planung", "3D-Entwurf inklusive"),
    ('<path d="M6.8 3.5h2.6l1.4 4-2.1 1.4a11.5 11.5 0 0 0 6.4 6.4l1.4-2.1 4 1.4v2.6a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.8 5.7a2 2 0 0 1 2-2.2z"/>',
     "Notdienst", "24/7 erreichbar"),
]
hs_cards = "".join(f'<span class="hs-card"><span class="hs-ic">{_hs_svg(ic)}</span><span><b>{t}</b><small>{d}</small></span></span>'
                   for ic, t, d in HS_CARDS)
HERO_STAGE = f'''<div class="stage fade-up d3" aria-hidden="true">
      <div class="screen">
        <div class="screen-bar"><i></i><i></i><i></i><span class="screen-url">{HS_LOCK}<span>ihre-firma.de</span></span><span class="screen-load"></span></div>
        <div class="hs">
          <div class="hs-nav">
            <span class="hs-logo"><span class="hs-mark">{HS_MARK}</span>Ihre Firma</span>
            <span class="hs-links"><span>Leistungen</span><span>Projekte</span><span>Über uns</span><span>Kontakt</span></span>
            <span class="hs-cta">Angebot anfragen</span>
            <span class="hs-burger"></span>
          </div>
          <div class="hs-hero">
            <div class="hs-copy">
              <span class="hs-kick">Meisterbetrieb seit 2009</span>
              <div class="mock-h">Ihr Handwerk.<br>Online sichtbar.</div>
              <p class="mock-p">Moderne Website, schnell geladen und bei Google gut gefunden.</p>
              <div class="hs-btns"><span class="hs-btn hs-main">Termin anfragen{HS_ARROW}</span><span class="hs-btn">Leistungen</span></div>
              <div class="hs-trust">{HS_STARS}<span>Top bewertet auf Google</span></div>
            </div>
            <div class="hs-visual">{HS_HOUSE}<span class="hs-tag"><b>Neubau Einfamilienhaus</b><small>Referenzprojekt</small></span><span class="hs-dots"><i></i><i></i><i></i></span></div>
          </div>
          <div class="hs-cards">{hs_cards}</div>
        </div>
        <span class="hs-cursor">{HS_POINTER}{HS_HAND}</span>
      </div>
      <div class="float f1" data-depth="18"><span class="ic">+1</span><span><b>Neue Anfrage</b><small>über das Kontaktformular</small></span></div>
      <div class="float f2" data-depth="-14"><span class="ic ok">{HS_SHIELD}</span><span><b>SSL &amp; Backup aktiv</b><small>täglich, automatisch</small></span></div>
      <div class="float f3" data-depth="10"{PS_STYLE}><span class="ic ps">{HS_RING}<i{PS_CLASS}>{PS_WERT}</i></span><span><b>PageSpeed {PS_WERT}/100</b><small>{PS_ART} gemessen</small></span></div>
    </div>'''

SECTORS = ["Handwerk", "Gastronomie", "Arztpraxen", "Kanzleien", "Immobilien", "Einzelhandel", "Fitness", "Beauty", "Logistik", "Beratung", "Hotels", "Vereine"]
marquee = "".join(f"<span>{s}</span>" for s in SECTORS) * 2

index_body = f'''<section class="hero">
  <canvas aria-hidden="true"></canvas>
  <div class="wrap hero-inner">
    <a class="pill fade-up" href="ueber-uns.html"><b>1.000+</b> Kunden vertrauen Nexora</a>
    <h1>
      <span class="line" aria-hidden="true"><span>Websites, die</span></span>
      <span class="line" aria-hidden="true"><span><span class="rotator"><span class="grad-text on">überzeugen.</span><span class="grad-text">verkaufen.</span><span class="grad-text">begeistern.</span><span class="grad-text">wachsen.</span></span></span></span>
      <span class="sr-only">Websites, die überzeugen.</span>
    </h1>
    <p class="lede fade-up d1">Nexora plant, gestaltet und betreut Ihre Website. Kaufen Sie sie einmalig oder mieten Sie sie zum festen Monatspreis, mit Hosting, Wartung und Support aus einer Hand.</p>
    <div class="hero-actions fade-up d2">
      <a class="btn btn--grad magnetic" href="termin.html">Kostenlose Beratung buchen {ARR}</a>
      <a class="btn btn--ghost" href="leistungen.html">Leistungen &amp; Preise</a>
    </div>
    {HERO_STAGE}
  </div>
</section>

<p class="sr-only">Branchen, für die wir arbeiten: {", ".join(SECTORS)}.</p>
<div class="marquee" aria-hidden="true"><div class="marquee-track">{marquee}</div></div>

<section class="section" aria-labelledby="what-h">
  <div class="wrap">
    <div class="head head--split">
      <div style="display:grid;gap:22px"><span class="eyebrow">Was wir machen</span><h2 id="what-h" class="reveal">Alles, was Ihre Website braucht. Aus einer Hand.</h2></div>
      <p class="lede reveal" data-d="1">Design, Technik, Hosting und Pflege. Sie haben eine Ansprechperson und müssen sich um nichts selbst kümmern.</p>
    </div>
    <div class="bento">
      {studio_card()}
      <article class="card b-2 reveal" data-d="1">
        <span class="k">Performance</span>
        <h3>Schnell geladen</h3>
        <p>Kurze Ladezeiten halten Besucher auf der Seite und helfen bei Google.{PS_SATZ}</p>
        <div class="viz" aria-hidden="true">
          <div class="gauge"{PS_STYLE}>
            <svg viewBox="0 0 100 100"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6A1BD6"/><stop offset="1" stop-color="#1667F0"/></linearGradient></defs><circle class="trk" cx="50" cy="50" r="42"/><circle class="val" cx="50" cy="50" r="42"/></svg>
            <div><b data-count="{PS_WERT}">{PS_WERT}</b><small>PageSpeed<br>{PS_ART}</small></div>
          </div>
          <ul class="vitals"><li><span>Ladezeit (LCP)</span><b>{PS_VITALS[0]}</b></li><li><span>Stabilität (CLS)</span><b>{PS_VITALS[1]}</b></li><li><span>Reaktion (TBT)</span><b>{PS_VITALS[2]}</b></li></ul>
        </div>
      </article>
      <article class="card b-3 reveal">
        <span class="k">Hosting</span>
        <h3>Sicher gehostet</h3>
        <p>SSL, Backups und Überwachung sind bei der Miete inklusive.</p>
        <div class="viz" aria-hidden="true"><div class="uptime"></div><div class="mono-row">{UPTIME_ROW}</div></div>
      </article>
      <article class="card b-4 reveal" data-d="1">
        <span class="k">SEO</span>
        <h3>Bei Google gefunden</h3>
        <p>Saubere Technik und gute Inhalte bringen Sie nach vorn.</p>
        <div class="viz serp" aria-hidden="true"><div class="you"><b>1</b>ihre-firma.de</div><div><b>2</b>mitbewerber-a.de</div><div><b>3</b>mitbewerber-b.de</div></div>
      </article>
      <article class="card b-5 reveal" data-d="2">
        <span class="k">Support</span>
        <h3>Persönlich erreichbar</h3>
        <p>Eine feste Ansprechperson, die Ihr Projekt kennt.</p>
        <div class="viz chat" aria-hidden="true"><span class="me">Können wir die Öffnungszeiten ändern?</span><span>Klar, ist erledigt und schon online.</span><span class="me">Super, danke!</span></div>
      </article>
    </div>
  </div>
</section>

{stats()}

<section class="section" aria-labelledby="price-h">
  <div class="wrap">
    <div class="head head--center">
      <span class="eyebrow">Leistungen &amp; Preise</span>
      <h2 id="price-h" class="reveal">Drei Wege zu Ihrer neuen Website.</h2>
      <p class="lede reveal" data-d="1">Kaufen, mieten oder betreuen lassen. Sie wählen das Modell, das zu Ihrem Budget passt.</p>
    </div>
    {plans(True)}
  </div>
</section>

<section class="section" style="padding-top:0" aria-labelledby="proc-h">
  <div class="wrap process">
    <div class="process-side">
      <span class="eyebrow">Ablauf</span>
      <h2 id="proc-h" class="reveal">In vier Schritten online.</h2>
      <p class="lede reveal" data-d="1">Klare Schritte, feste Ansprechperson und ein Termin, auf den Sie sich verlassen können.</p>
      <div class="reveal" data-d="2"><a class="btn magnetic" href="termin.html">Schritt 1 starten {ARR}</a></div>
    </div>
    <div class="timeline">
      <span class="fill" aria-hidden="true"></span>
      <div class="tl-item" data-obs><span class="n">Schritt 1</span><h3>Beratung</h3><p>Im kostenlosen Gespräch klären wir Ziele, Umfang und Budget. Danach bekommen Sie ein klares Angebot.</p><span class="dur">30 Minuten</span></div>
      <div class="tl-item" data-obs><span class="n">Schritt 2</span><h3>Konzept &amp; Design</h3><p>Wir entwerfen Struktur und Look Ihrer Website. Sie geben Feedback, bis alles passt.</p><span class="dur">ca. 1 Woche</span></div>
      <div class="tl-item" data-obs><span class="n">Schritt 3</span><h3>Entwicklung</h3><p>Wir setzen alles technisch um: schnell, sicher und für Suchmaschinen vorbereitet.</p><span class="dur">ca. 1 Woche</span></div>
      <div class="tl-item" data-obs><span class="n">Schritt 4</span><h3>Livegang &amp; Betreuung</h3><p>Ihre Website geht online. Auf Wunsch kümmern wir uns danach um Hosting, Updates und Änderungen.</p><span class="dur">laufend</span></div>
    </div>
  </div>
</section>

{reviews()}

{team_section(home=True)}

<section class="section" style="padding-top:0" aria-labelledby="job-h">
  <div class="wrap">
    <div class="head head--split">
      <div style="display:grid;gap:22px"><span class="eyebrow">Karriere</span><h2 id="job-h" class="reveal">Wir wachsen. Wachse mit uns.</h2></div>
      <p class="lede reveal" data-d="1">Für unser Team suchen wir Menschen, die Lust auf starke Websites und zufriedene Kunden haben.</p>
    </div>
    <div class="split-cards">
      <a class="job-card reveal" href="karriere.html#vertrieb">
        <span class="live"><i></i>Vertriebler gesucht</span>
        <h3>Vertrieb (m/w/d)</h3>
        <p class="muted">Du gewinnst neue Kunden und berätst sie zu Kauf, Miete und Betreuung. Fixum plus Provision.</p>
        <span class="go">Stelle ansehen <span aria-hidden="true">→</span></span>
      </a>
      <a class="job-card reveal" data-d="1" href="karriere.html#developer">
        <span class="live"><i></i>Developer gesucht</span>
        <h3>Developer (m/w/d)</h3>
        <p class="muted">Du setzt Kundenwebsites technisch sauber und schnell um. Frontend, CMS und Performance.</p>
        <span class="go">Stelle ansehen <span aria-hidden="true">→</span></span>
      </a>
    </div>
  </div>
</section>

{cta()}
'''

# ================= Leistungen =================
INCL = [("server", "Hosting", "Schnelle Server, ohne dass Sie sich kümmern müssen"), ("globe", "Domain", "Ihre Wunschadresse, eingerichtet und verwaltet"),
        ("lock", "SSL-Zertifikat", "Verschlüsselte Verbindung und das Schloss im Browser"), ("refresh", "Updates", "Technik und Plugins immer aktuell"),
        ("archive", "Tägliche Backups", "Ihre Daten sind jederzeit wiederherstellbar"), ("edit", "Änderungen", "Texte, Bilder, Öffnungszeiten auf Zuruf"),
        ("activity", "Monitoring", "Wir merken Probleme, bevor Ihre Kunden es tun"), ("user", "Ansprechperson", "Eine Person, die Ihr Projekt kennt")]
incl = "".join(f'<div class="reveal" data-d="{i%4}">{icon(k)}<span><b>{t}</b><span>{d}</span></span></div>' for i, (k, t, d) in enumerate(INCL))

FAQ = [
    ("Was ist der Unterschied zwischen Kaufen und Mieten?", "Beim Kauf zahlen Sie einmalig ab 1.000 € und die Website gehört Ihnen. Hosting und Pflege können Sie dazubuchen. Bei der Miete zahlen Sie ab 150 € im Monat und bekommen alles inklusive: Hosting, Domain, Updates, Backups und Änderungen."),
    ("Wie lange dauert es, bis meine Website online ist?", "Eine typische Unternehmenswebsite ist in zwei bis drei Wochen online. Größere Projekte planen wir gemeinsam im Beratungsgespräch."),
    ("Kann ich später von Miete auf Kauf wechseln?", "Ja. Sprechen Sie uns an, dann rechnen wir den Wechsel transparent für Sie durch."),
    ("Betreut ihr auch Websites, die nicht von euch sind?", "Ja. Mit der Website-Betreuung übernehmen wir Wartung, Updates und Weiterentwicklung bestehender Seiten, auf Wunsch inklusive Umzug auf unser Hosting."),
    ("Muss ich mich um Texte und Bilder selbst kümmern?", "Nicht unbedingt. Wir helfen bei Texten, Bildauswahl und Struktur, damit Ihre Website von Anfang an überzeugt."),
    ("Was kostet das Beratungsgespräch?", "Nichts. Das Gespräch ist kostenlos und unverbindlich. Sie bekommen danach ein klares Angebot."),
]
faq = "".join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in FAQ)

ROWS = [("Einmalige Kosten", "ab 1.000 €", "–", "–"),
        ("Monatliche Kosten", "optional", "ab 150 €", "auf Anfrage"),
        ("Individuelles Design", '<span class="yes">✓</span>', '<span class="yes">✓</span>', "Erweiterungen"),
        ("Hosting, Domain, SSL", '<span class="opt">dazubuchbar</span>', '<span class="yes">✓ inklusive</span>', "auf Wunsch"),
        ("Updates und Sicherheit", '<span class="opt">dazubuchbar</span>', '<span class="yes">✓ inklusive</span>', '<span class="yes">✓</span>'),
        ("Inhalts&shy;änderungen", '<span class="opt">nach Aufwand</span>', '<span class="yes">✓ inklusive</span>', '<span class="yes">✓</span>'),
        ("Tägliche Backups", '<span class="opt">dazubuchbar</span>', '<span class="yes">✓ inklusive</span>', '<span class="yes">✓</span>'),
        ("Website gehört Ihnen", '<span class="yes">✓</span>', "während der Laufzeit gemietet", '<span class="yes">✓</span>'),
        ("Ideal für", "Feste Budgets, volle Kontrolle", "Planbare Kosten, null Aufwand", "Bestehende Websites")]
rows = "".join(f'<tr><th scope="row">{a}</th><td>{b}</td><td>{c}</td><td>{d}</td></tr>' for a, b, c, d in ROWS)

leist_body = f'''<section class="page-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Leistungen</p>
    <h1 class="reveal">Leistungen <span class="grad-text">&amp; Preise</span></h1>
    <p class="lede reveal" data-d="1">Kaufen, mieten oder betreuen lassen. Transparente Startpreise, klare Leistungen und ein festes Angebot nach der Beratung.</p>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">
    <h2 class="sr-only">Pakete und Preise</h2>
    {plans(False)}
    <p class="fine">Alle Preise zzgl. gesetzlicher MwSt. Laufzeit und Leistungsumfang legen wir im Beratungsgespräch gemeinsam fest.</p>
  </div>
</section>

<section class="section" style="padding-top:0" aria-labelledby="incl-h">
  <div class="wrap">
    <div class="head head--split">
      <div style="display:grid;gap:22px"><span class="eyebrow">Website mieten</span><h2 id="incl-h" class="reveal">Bei der Miete ist alles drin.</h2></div>
      <p class="lede reveal" data-d="1">Ein fester Monatspreis, keine Überraschungen. Diese Leistungen sind immer inklusive.</p>
    </div>
    <div class="incl">{incl}</div>
  </div>
</section>

<section class="section" style="padding-top:0" id="vergleich" aria-labelledby="cmp-h">
  <div class="wrap">
    <div class="head">
      <span class="eyebrow">Vergleich</span>
      <h2 id="cmp-h" class="reveal">Welches Modell passt zu Ihnen?</h2>
    </div>
    <div class="table-wrap reveal">
      <table class="compare">
        <thead><tr><th scope="col"><span class="sr-only">Leistung</span></th><th scope="col">Kaufen</th><th scope="col">Mieten</th><th scope="col">Betreuung</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="swipe-hint">Zum Vergleichen seitlich wischen →</p>
  </div>
</section>

{stats("Darum entscheiden sich Unternehmen für Nexora.")}

<section class="section" aria-labelledby="faq-h">
  <div class="wrap" style="display:grid;gap:48px;max-width:960px">
    <div class="head head--center" style="margin:0"><span class="eyebrow">Häufige Fragen</span><h2 id="faq-h" class="reveal">Gut zu wissen.</h2></div>
    <div class="faq reveal">{faq}</div>
  </div>
</section>

{cta("Bereit für Ihre neue Website?", "In 30 Minuten klären wir, welches Modell zu Ihnen passt, und Sie bekommen ein klares Angebot.")}
'''

# ================= Über uns =================
VALUES = [("search", "Klar statt kompliziert", "Wir erklären Technik so, dass jeder sie versteht, und machen Preise transparent."),
          ("activity", "Schnell statt ewig", "Die meisten Websites sind in zwei bis drei Wochen online. Ohne Abstriche bei der Qualität."),
          ("user", "Partner statt Dienstleister", "Wir bleiben nach dem Livegang an Ihrer Seite und entwickeln Ihre Website mit Ihnen weiter.")]
values = "".join(f'<article class="card reveal" data-d="{i}"><span class="ico">{icon(k)}</span><h3>{t}</h3><p>{d}</p></article>' for i, (k, t, d) in enumerate(VALUES))

about_body = f'''<section class="page-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Über uns</p>
    <h1 class="reveal">Your Vision, <span class="grad-text">Our Code.</span></h1>
    <p class="lede reveal" data-d="1">Wir sind Nexora, eine Webagentur für Unternehmen, die online professionell auftreten wollen, ohne sich um Technik kümmern zu müssen.</p>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap story">
    <p class="big-quote reveal">Eine gute Website ist kein Luxus. Sie ist das erste, was Ihre Kunden von Ihnen sehen.</p>
    <div class="story-text reveal" data-d="1">
      <p>Nexora ist mit einem einfachen Ziel gestartet: Unternehmen eine Website zu geben, die gut aussieht, schnell lädt und Kunden bringt. Zu einem Preis, der planbar ist.</p>
      <p>Heute betreuen wir über 1.000 Kunden, vom Handwerksbetrieb bis zur Kanzlei. Manche kaufen ihre Website einmalig, viele mieten sie zum festen Monatspreis und überlassen uns Hosting, Wartung und Änderungen.</p>
      <p>Was alle gemeinsam haben: eine feste Ansprechperson, schnelle Antworten und eine Website, auf die sie stolz sind.</p>
    </div>
  </div>
</section>

{stats()}

<section class="section" aria-labelledby="val-h">
  <div class="wrap">
    <div class="head"><span class="eyebrow">Wofür wir stehen</span><h2 id="val-h" class="reveal">Drei Versprechen an unsere Kunden.</h2></div>
    <div class="values">{values}</div>
  </div>
</section>

{team_section()}

{cta()}
'''

# ================= Karriere =================
PERKS = [("Flexibel arbeiten", "Remote, im Büro oder gemischt. Du entscheidest, wo du am besten arbeitest."),
         ("Faire Bezahlung", "Attraktives Gehalt, im Vertrieb mit Fixum und Provision ohne Deckel."),
         ("Kurze Wege", "Flache Hierarchien, schnelle Entscheidungen, direkter Draht zur Geschäftsführung."),
         ("Moderne Ausstattung", "Gute Hardware und die Tools, die du für deine Arbeit brauchst."),
         ("Weiterbildung", "Budget und Zeit für Kurse, Konferenzen und neue Technologien."),
         ("Echte Wirkung", "Deine Arbeit ist für über 1.000 Kunden direkt sichtbar.")]
perks = "".join(f'<div class="perk reveal" data-d="{i%3}"><b>{t}</b><span>{d}</span></div>' for i, (t, d) in enumerate(PERKS))

def job(id_, status, title, tags, intro, tasks, profile):
    t = "".join(f"<span>{x}</span>" for x in tags)
    a = "".join(f"<li>{x}</li>" for x in tasks)
    p = "".join(f"<li>{x}</li>" for x in profile)
    return f'''<article class="job reveal" id="{id_}">
      <div style="display:grid;gap:20px;align-content:start">
        <span class="live"><i></i>{status}</span>
        <h2>{title}</h2>
        <div class="job-tags">{t}</div>
        <p class="muted">{intro}</p>
        <div><a class="btn btn--grad magnetic" href="bewerbung.html?stelle={id_}">Jetzt bewerben {ARR}</a></div>
      </div>
      <div class="job-cols">
        <div><h3>Deine Aufgaben</h3><ul>{a}</ul></div>
        <div><h3>Das bringst du mit</h3><ul>{p}</ul></div>
      </div>
    </article>'''

jobs = job("vertrieb", "Vertriebler gesucht", "Vertrieb (m/w/d)", ["Vollzeit oder Teilzeit", "Remote oder vor Ort", "Fixum + Provision"],
           "Du bist der erste Kontakt für neue Kunden und zeigst ihnen, wie sie mit einer starken Website mehr erreichen.",
           ["Neue Kunden gewinnen, telefonisch und persönlich", "Beratung zu Kauf, Miete und Betreuung", "Angebote erstellen und Abschlüsse machen", "Bestandskunden betreuen und weiterentwickeln"],
           ["Erfahrung im Vertrieb, gern B2B", "Freude am Telefonieren und an Abschlüssen", "Sicheres, sympathisches Auftreten", "Interesse an Websites und digitalen Themen"]) + \
       job("developer", "Developer gesucht", "Developer (m/w/d)", ["Vollzeit", "Remote oder vor Ort", "Frontend &amp; CMS"],
           "Du setzt Kundenwebsites technisch um und sorgst dafür, dass sie schnell, sicher und sauber gebaut sind.",
           ["Websites nach Design umsetzen", "Arbeit mit HTML, CSS, JavaScript und CMS", "Performance und SEO-Technik optimieren", "Bestehende Kundenseiten pflegen und erweitern"],
           ["Solide Erfahrung im Frontend", "Erfahrung mit gängigen CMS", "Auge für Details und gute Performance", "Selbstständige, strukturierte Arbeitsweise"])

STEPS = [("Bewerbung schicken", "Formular ausfüllen, Lebenslauf hochladen, fertig. Ein Anschreiben brauchst du nicht."),
         ("Kennenlernen", "Ein lockeres Gespräch per Video. Wir erzählen von uns, du von dir."),
         ("Fachgespräch", "Wir schauen uns gemeinsam eine typische Aufgabe an. Kein Stress, kein Theater."),
         ("Willkommen", "Zusage, Onboarding und los geht's mit deinem ersten Projekt.")]
steps = "".join(f'<div class="tl-item" data-obs><span class="n">Schritt {i+1}</span><h3>{t}</h3><p>{d}</p></div>' for i, (t, d) in enumerate(STEPS))

career_body = f'''<section class="page-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Karriere</p>
    <h1 class="reveal">Wir wachsen. <span class="grad-text">Wachse mit uns.</span></h1>
    <p class="lede reveal" data-d="1">Über 1.000 Kunden und es werden jeden Monat mehr. Dafür suchen wir Verstärkung im Vertrieb und in der Entwicklung.</p>
    <div class="hero-actions reveal" data-d="2" style="justify-content:flex-start;margin-top:30px">
      <a class="btn btn--ghost" href="#vertrieb">Vertriebler gesucht</a>
      <a class="btn btn--ghost" href="#developer">Developer gesucht</a>
    </div>
  </div>
</section>

<section class="section" style="padding-top:0">
  <div class="wrap">{jobs}</div>
</section>

<section class="section dark" aria-labelledby="perk-h">
  <div class="wrap">
    <div class="head"><span class="eyebrow">Was dich erwartet</span><h2 id="perk-h" class="reveal">Gute Arbeit braucht gute Bedingungen.</h2></div>
    <div class="perks">{perks}</div>
  </div>
</section>

<section class="section" aria-labelledby="apply-h">
  <div class="wrap process">
    <div class="process-side">
      <span class="eyebrow">Bewerbung</span>
      <h2 id="apply-h" class="reveal">So einfach geht's.</h2>
      <p class="lede reveal" data-d="1">Bewirb dich in zwei Minuten über unser Formular. Wir melden uns innerhalb weniger Tage.</p>
      <div class="apply-cta reveal" data-d="2"><a class="btn btn--grad magnetic" href="bewerbung.html">Jetzt bewerben {ARR}</a><span>Lieber per E-Mail? <a href="mailto:{CAREER_MAIL}">{CAREER_MAIL}</a></span></div>
    </div>
    <div class="timeline"><span class="fill" aria-hidden="true"></span>{steps}</div>
  </div>
</section>
'''

# ================= Termin =================
CALENDLY = "https://calendly.com/linus-bbgnet/30min"   # Link zum Buchungskalender
CALENDLY_CONSENT = False  # Lennos Wahl vom 17.11.2026: sofort laden. True = Kalender erst nach Klick auf "Kalender anzeigen" laden (datensparsamer), False = sofort laden
termin_body = f'''<section class="page-hero" style="padding-bottom:clamp(64px,8vw,120px)">
  <div class="wrap book">
    <div class="book-side book-intro">
      <p class="crumbs"><a href="index.html">Start</a> / Beratungstermin</p>
      <h1 class="reveal">Beratungstermin <span class="grad-text">buchen</span></h1>
      <p class="lede reveal" data-d="1">Wählen Sie einen freien Termin. In 30 Minuten klären wir, was Ihre Website braucht, was sie kostet und wann sie online gehen kann.</p>
    </div>
    <div class="book-side book-details">
      <ul class="facts reveal" data-d="2">
        <li><span>Dauer</span>30 Minuten</li>
        <li><span>Format</span>Telefon oder Videocall</li>
        <li><span>Kosten</span>Kostenlos und unverbindlich</li>
        <li><span>Ergebnis</span>Ein klares Angebot</li>
      </ul>
      <div class="reveal" data-d="3" style="display:grid;gap:16px">
        <span class="eyebrow">Darüber sprechen wir</span>
        <ol class="agenda"><li>Ihr Unternehmen und Ihre Ziele</li><li>Kaufen, mieten oder betreuen lassen</li><li>Umfang, Zeitplan und Budget</li><li>Nächste Schritte und Angebot</li></ol>
      </div>
      <div class="alt-links reveal" data-d="3">
        <a class="wa-inline" {WA_ATTRS}><span class="wa-ic">{WA_SVG}</span><span><b>Lieber schreiben?</b><small>Schicken Sie uns Ihre Frage per WhatsApp.</small></span><span class="arr" aria-hidden="true">↗</span></a>
        <a class="wa-inline wa-inline--mail" href="kontakt.html"><span class="mail-ic">{icon("mail")}</span><span><b>Lieber per E-Mail?</b><small>Anfrage über das Kontaktformular senden.</small></span>{ARR}</a>
      </div>
    </div>
    <div class="book-cal reveal" data-d="1">
      <div class="cal" id="cal" data-url="{CALENDLY}" data-consent="{1 if CALENDLY_CONSENT else 0}">
        <!-- Wird per JavaScript durch den Calendly-Kalender ersetzt (Einstellungen: CALENDLY und CALENDLY_CONSENT in build.py).
             Mit CALENDLY_CONSENT lädt der Kalender erst nach Klick auf "Kalender anzeigen".
             Die Karte mit dem direkten Link bleibt, wenn der Kalender nicht eingebettet werden kann. -->
        <div class="cal-ph">
          <div class="cal-host"><img src="assets/logo-mark-144.png" alt="" width="46" height="46"><div><b>Kostenlose Beratung</b><span>30 Min · Telefon oder Video</span></div></div>
          <div class="cal-cta">
            <h2>Freie Termine in Echtzeit.</h2>
            <p>Wählen Sie im Kalender einen passenden Termin. Die Bestätigung mit allen Details kommt sofort per E-Mail.</p>
            <div class="cal-ask" hidden>
              <button class="btn btn--grad magnetic cal-load" type="button">Kalender anzeigen {ARR}</button>
              <small>Erst mit diesem Klick lädt der Kalender von Calendly. Dabei werden Daten an Calendly übertragen. <a href="datenschutz.html#calendly">Mehr dazu</a> · <a href="{CALENDLY}" target="_blank" rel="noopener">Direkt bei Calendly öffnen ↗</a></small>
            </div>
            <div class="cal-direct">
              <a class="btn btn--grad magnetic" href="{CALENDLY}" target="_blank" rel="noopener">Freie Termine ansehen <span class="arr" aria-hidden="true">↗</span></a>
              <small>Der Kalender öffnet sich bei Calendly in einem neuen Tab.</small>
            </div>
          </div>
        </div>
      </div>
      <p class="cal-alt">Kalender lädt nicht? <a href="{CALENDLY}" target="_blank" rel="noopener">Termin direkt bei Calendly buchen ↗</a></p>
    </div>
  </div>
</section>
'''

page("index.html", "Nexora Webagentur", "Nexora baut, hostet und betreut Websites für Unternehmen. Website kaufen ab 1.000 €, mieten ab 150 € im Monat inklusive Hosting.", "index.html", index_body)
page("leistungen.html", "Leistungen & Preise · Nexora", "Website kaufen ab 1.000 €, Website mieten ab 150 € im Monat inklusive Hosting, Website-Betreuung auf Anfrage.", "leistungen.html", leist_body)
page("ueber-uns.html", "Über uns · Nexora", "Nexora ist eine Webagentur mit über 1.000 Kunden. Your Vision, Our Code.", "ueber-uns.html", about_body)
page("karriere.html", "Karriere · Nexora", "Nexora sucht Vertriebler und Developer (m/w/d).", "karriere.html", career_body)
page("termin.html", "Beratungstermin · Nexora", "Buchen Sie Ihr kostenloses Beratungsgespräch mit Nexora.", "", termin_body, cta_href="#cal")

# ================= Bewerbung =================
FORM_ACTION = "/api/bewerbung" if FORM_BACKEND == "vercel" else "bewerbung.php"
MAX_MB = 4 if FORM_BACKEND == "vercel" else 10   # Vercel nimmt höchstens 4,5 MB pro Anfrage an
POSITIONS = [("vertrieb", "Vertrieb (m/w/d)"), ("developer", "Developer (m/w/d)"), ("initiativ", "Initiativbewerbung")]
pos_opts = "".join(f'<label class="seg"><input type="radio" name="stelle" value="{v}"{" checked" if i == 0 else ""}><span>{t}</span></label>' for i, (v, t) in enumerate(POSITIONS))

apply_body = f"""<section class="page-hero" style="padding-bottom:clamp(64px,8vw,120px)">
  <div class="wrap book">
    <div class="book-side book-intro">
      <p class="crumbs"><a href="index.html">Start</a> / <a href="karriere.html">Karriere</a> / Bewerbung</p>
      <h1 class="reveal">Jetzt <span class="grad-text">bewerben</span></h1>
      <p class="lede reveal" data-d="1">Zwei Minuten, ein Formular. Lebenslauf hochladen oder Profil verlinken, ein Anschreiben brauchst du nicht.</p>
    </div>
    <div class="book-side book-details">
      <ul class="facts reveal" data-d="2">
        <li><span>Dauer</span>ca. 2 Minuten</li>
        <li><span>Unterlagen</span>Lebenslauf, gern als PDF</li>
        <li><span>Antwort</span>innerhalb weniger Tage</li>
      </ul>
      <div class="reveal" data-d="3" style="display:grid;gap:16px">
        <span class="eyebrow">So geht es weiter</span>
        <ol class="agenda"><li>Wir lesen deine Bewerbung persönlich</li><li>Kennenlernen per Video</li><li>Fachgespräch mit einer typischen Aufgabe</li><li>Zusage und Onboarding</li></ol>
      </div>
    </div>
    <div class="book-cal reveal" data-d="1">
      <form class="apply-form" id="applyForm" action="{FORM_ACTION}" method="post" enctype="multipart/form-data" novalidate data-mail="{CAREER_MAIL}" data-max-mb="{MAX_MB}">
        <div class="af-head"><h2>Deine Bewerbung</h2><p>Felder mit „optional“ kannst du leer lassen.</p></div>
        <fieldset class="af-field">
          <legend>Stelle</legend>
          <div class="segs">{pos_opts}</div>
        </fieldset>
        <label class="af-field"><span>Vor- und Nachname</span><input type="text" name="name" autocomplete="name" maxlength="120" required></label>
        <div class="af-grid">
          <label class="af-field"><span>E-Mail</span><input type="email" name="email" autocomplete="email" maxlength="160" required></label>
          <label class="af-field"><span>Telefon <i>optional</i></span><input type="tel" name="telefon" autocomplete="tel" maxlength="40"></label>
        </div>
        <div class="af-field">
          <span>Lebenslauf <i>optional</i></span>
          <label class="drop">
            <input type="file" name="lebenslauf" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png">
            <span class="drop-ic">{icon("upload")}</span>
            <span class="drop-txt"><b>Datei auswählen</b> oder hierher ziehen<small>PDF, Word oder Bild, max.&nbsp;{MAX_MB}&nbsp;MB</small><em class="drop-name"></em></span>
          </label>
        </div>
        <label class="af-field"><span>LinkedIn, Xing oder Portfolio <i>optional</i></span><input type="text" name="link" inputmode="url" autocomplete="url" placeholder="https://" maxlength="300"></label>
        <label class="af-field"><span>Erzähl uns kurz von dir <i>optional</i></span><textarea name="nachricht" rows="4" maxlength="5000" placeholder="Was machst du gerade, und was reizt dich an Nexora?"></textarea></label>
        <label class="af-check"><input type="checkbox" name="datenschutz" value="ja" required><span>Ich bin einverstanden, dass Nexora meine Angaben zur Bearbeitung meiner Bewerbung verarbeitet. Mehr dazu in der <a href="datenschutz.html#bewerbung">Datenschutzerklärung</a>.</span></label>
        <div class="hp" aria-hidden="true"><label>Firma <input type="text" name="firma" tabindex="-1" autocomplete="off"></label></div>
        <div class="af-actions">
          <button class="btn btn--grad magnetic af-submit" type="submit"><span class="af-label">Bewerbung absenden</span> {ARR}</button>
          <p class="af-msg" role="alert"></p>
          <p class="af-nojs" id="fehler">Das Senden hat leider nicht geklappt. Schick deine Bewerbung gern direkt an <a href="mailto:{CAREER_MAIL}">{CAREER_MAIL}</a>.</p>
        </div>
        <div class="af-done" id="gesendet" hidden>
          <span class="af-done-ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7"/></svg></span>
          <h2>Danke für deine Bewerbung!</h2>
          <p>Sie ist gut bei uns angekommen. Wir melden uns innerhalb weniger Tage bei dir, eine Bestätigung ist schon unterwegs in dein Postfach.</p>
          <a class="btn btn--ghost" href="karriere.html">Zurück zur Karriereseite</a>
        </div>
      </form>
    </div>
  </div>
</section>
"""
page("bewerbung.html", "Bewerbung · Nexora", "Bewirb dich bei Nexora als Vertriebler oder Developer (m/w/d), in zwei Minuten.", "karriere.html", apply_body)

# ================= Kontakt =================
CONTACT_ACTION = "/api/anfrage" if FORM_BACKEND == "vercel" else "anfrage.php"
ANLIEGEN = [("kaufen", "Website kaufen"), ("mieten", "Website mieten"), ("betreuung", "Website-Betreuung"), ("sonstiges", "Etwas anderes")]
topic_opts = "".join(f'<label class="seg"><input type="radio" name="anliegen" value="{v}"><span>{t}</span></label>' for v, t in ANLIEGEN)

contact_body = f"""<section class="page-hero" style="padding-bottom:clamp(64px,8vw,120px)">
  <div class="wrap book">
    <div class="book-side book-intro">
      <p class="crumbs"><a href="index.html">Start</a> / Kontakt</p>
      <h1 class="reveal">Anfrage <span class="grad-text">senden</span></h1>
      <p class="lede reveal" data-d="1">Erzählen Sie uns kurz, was Sie vorhaben. Wir melden uns {ANTWORTZEIT} mit einer ersten Einschätzung.</p>
    </div>
    <div class="book-side book-details">
      <ul class="facts reveal" data-d="2">
        <li><span>Antwort</span>{ANTWORTZEIT}</li>
        <li><span>Kosten</span>Kostenlos und unverbindlich</li>
        <li><span>E-Mail</span><a href="mailto:{INFO_MAIL}">{INFO_MAIL}</a></li>
      </ul>
      <div class="reveal" data-d="3" style="display:grid;gap:16px">
        <span class="eyebrow">So geht es weiter</span>
        <ol class="agenda"><li>Wir lesen Ihre Anfrage persönlich</li><li>Rückmeldung per E-Mail oder Telefon</li><li>Auf Wunsch ein kostenloses Beratungsgespräch</li><li>Ein klares Angebot</li></ol>
      </div>
      <div class="alt-links reveal" data-d="3">
        <a class="wa-inline wa-inline--mail" href="termin.html"><span class="mail-ic">{icon("phone")}</span><span><b>Lieber direkt sprechen?</b><small>Kostenlosen Beratungstermin buchen.</small></span>{ARR}</a>
        <a class="wa-inline" {WA_ATTRS}><span class="wa-ic">{WA_SVG}</span><span><b>Lieber per WhatsApp?</b><small>Schreiben Sie uns direkt im Chat.</small></span><span class="arr" aria-hidden="true">↗</span></a>
      </div>
    </div>
    <div class="book-cal reveal" data-d="1">
      <form class="apply-form" id="contactForm" action="{CONTACT_ACTION}" method="post" novalidate data-mail="{INFO_MAIL}">
        <div class="af-head"><h2>Ihre Anfrage</h2><p>Felder mit „optional“ können Sie leer lassen.</p></div>
        <fieldset class="af-field">
          <legend>Worum geht es?</legend>
          <div class="segs">{topic_opts}</div>
        </fieldset>
        <div class="af-grid">
          <label class="af-field"><span>Vor- und Nachname</span><input type="text" name="name" autocomplete="name" maxlength="120" required></label>
          <label class="af-field"><span>Unternehmen <i>optional</i></span><input type="text" name="unternehmen" autocomplete="organization" maxlength="120"></label>
        </div>
        <div class="af-grid">
          <label class="af-field"><span>E-Mail</span><input type="email" name="email" autocomplete="email" maxlength="160" required></label>
          <label class="af-field"><span>Telefon <i>optional</i></span><input type="tel" name="telefon" autocomplete="tel" maxlength="40"></label>
        </div>
        <label class="af-field"><span>Ihre aktuelle Website <i>optional</i></span><input type="text" name="website" inputmode="url" autocomplete="url" placeholder="https://" maxlength="300"></label>
        <label class="af-field"><span>Ihre Nachricht</span><textarea name="nachricht" rows="5" maxlength="5000" required placeholder="Was haben Sie vor? Zum Beispiel: neue Website für unseren Betrieb, etwa fünf Seiten, Start im Frühjahr."></textarea></label>
        <label class="af-check"><input type="checkbox" name="datenschutz" value="ja" required><span>Ich bin einverstanden, dass Nexora meine Angaben zur Bearbeitung meiner Anfrage verarbeitet. Mehr dazu in der <a href="datenschutz.html#anfrage">Datenschutzerklärung</a>.</span></label>
        <div class="hp" aria-hidden="true"><label>Firma <input type="text" name="firma" tabindex="-1" autocomplete="off"></label></div>
        <div class="af-actions">
          <button class="btn btn--grad magnetic af-submit" type="submit"><span class="af-label">Anfrage senden</span> {ARR}</button>
          <p class="af-msg" role="alert"></p>
          <p class="af-nojs" id="fehler">Das Senden hat leider nicht geklappt. Schreiben Sie uns gern direkt an <a href="mailto:{INFO_MAIL}">{INFO_MAIL}</a>.</p>
        </div>
        <div class="af-done" id="gesendet" hidden>
          <span class="af-done-ic"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7"/></svg></span>
          <h2>Vielen Dank für Ihre Anfrage!</h2>
          <p>Sie ist gut bei uns angekommen. Wir melden uns {ANTWORTZEIT}, eine Bestätigung ist schon unterwegs in Ihr Postfach.</p>
          <a class="btn btn--ghost" href="leistungen.html">Leistungen ansehen</a>
        </div>
      </form>
    </div>
  </div>
</section>
"""
page("kontakt.html", "Kontakt · Nexora", f"Schreiben Sie Nexora: neue Website, Website mieten oder Betreuung. Antwort {ANTWORTZEIT}.", "kontakt.html", contact_body)

# Versand der Formulare: Vercel-Funktionen oder PHP-Skripte (nur das gewählte landet im Ausgabeordner)
_here = pathlib.Path(__file__).resolve().parent
_basis = (_here / "formular-basis.js").read_text(encoding="utf-8")
for _name, _to in (("bewerbung", CAREER_MAIL), ("anfrage", INFO_MAIL)):
    _js, _php = OUT / "api" / f"{_name}.js", OUT / f"{_name}.php"
    if FORM_BACKEND == "vercel":
        (OUT / "api").mkdir(exist_ok=True)
        _tpl = (_here / f"{_name}.vercel.js").read_text(encoding="utf-8")
        _tpl = (_tpl.replace("/*__BASIS__*/", _basis.rstrip("\n")).replace("__EMPFAENGER__", _to).replace("__MAX_MB__", str(MAX_MB))
                    .replace("__SITE_URL__", SITE_URL).replace("__ANTWORTZEIT__", ANTWORTZEIT))
        _js.write_text(_tpl, encoding="utf-8")
        if _php.exists():
            _php.unlink()
    else:
        if _js.exists():
            _js.unlink()
        _tpl = (_here / f"{_name}.template.php").read_text(encoding="utf-8")
        _php.write_text(_tpl.replace("__EMPFAENGER__", _to).replace("__SITE_URL__", SITE_URL).replace("__ANTWORTZEIT__", ANTWORTZEIT), encoding="utf-8")

# ================= Impressum / Datenschutz (Vorlagen) =================
def ph(t):
    return f'<span class="ph">{t}</span>'

ZEIGE_PLATZHALTER = not LIVE   # live werden leere Felder weggelassen statt markiert

def wert(v, platzhalter):
    if v:
        return _html.escape(v)
    return ph(platzhalter) if ZEIGE_PLATZHALTER else ""

def zeilen(*teile):
    # verbindet nur die nicht leeren Teile, jeweils mit Zeilenumbruch
    return "<br>".join(t for t in teile if t)

IMPRESSUM_OFFEN = not all([STRASSE, PLZ_ORT, TELEFON, REGISTERGERICHT, HRB]) or (UST_ID_OFFEN and not UST_ID)
IMP_NOTE = ('<p class="legal-note">Vorlage: Die markierten Felder müssen vor dem Livegang mit den echten Firmendaten ausgefüllt werden.</p>'
            if IMPRESSUM_OFFEN and ZEIGE_PLATZHALTER else "")
if UST_ID:
    IMP_UST = f'<section><h2>Umsatzsteuer-ID</h2><p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: {_html.escape(UST_ID)}</p></section>'
elif UST_ID_OFFEN and ZEIGE_PLATZHALTER:
    IMP_UST = f'<section><h2>Umsatzsteuer-ID</h2><p>Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: {ph("USt-IdNr.")}</p></section>'
else:
    IMP_UST = ""

CAL_DS = ("Der Kalender wird erst geladen, wenn Sie auf der Seite „Beratungstermin“ auf „Kalender anzeigen“ klicken. Erst dann werden Daten wie Ihre IP-Adresse an Calendly übertragen."
          if CALENDLY_CONSENT else "Der Kalender ist auf der Seite „Beratungstermin“ eingebunden und wird beim Aufruf dieser Seite direkt von Calendly geladen. Dabei werden Daten wie Ihre IP-Adresse an Calendly übertragen, und Calendly kann Cookies setzen.")
COOKIE_DS = ("Diese Website setzt selbst keine Cookies und speichert nichts in Ihrem Browser. Cookies kann nur Calendly setzen, und zwar erst, wenn Sie den Kalender laden (siehe Abschnitt 6)."
             if CALENDLY_CONSENT else "Diese Website setzt selbst keine Cookies und speichert nichts in Ihrem Browser. Cookies kann nur der Calendly-Kalender auf der Seite „Beratungstermin“ setzen (siehe Abschnitt 6).")
MAIL_ANBIETER = "STRATO GmbH (Berlin)"   # Postfach und Versand der Formular-Mails
CAL_RG = ("Ihre Einwilligung, die Sie mit dem Klick auf „Kalender anzeigen“ erteilen (Art. 6 Abs. 1 lit. a DSGVO, § 25 Abs. 1 TDDDG). Sie können sie jederzeit für die Zukunft widerrufen, indem Sie die Seite neu laden und den Kalender nicht mehr öffnen"
          if CALENDLY_CONSENT else "unser berechtigtes Interesse an einer einfachen Online-Terminvereinbarung (Art. 6 Abs. 1 lit. f DSGVO)")
FORM_DS = ("Die Formulare werden über eine Funktion auf Servern von Vercel in Frankfurt am Main verarbeitet und per E-Mail über " + MAIL_ANBIETER + " an uns übermittelt."
           if FORM_BACKEND == "vercel" else "Die Formulare werden auf dem Webserver verarbeitet und per E-Mail an uns übermittelt.")

DS_STAND = "November 2026"
DS_NOTE = ('<p class="legal-note">Die markierten Felder werden noch ergänzt.</p>' if IMPRESSUM_OFFEN and ZEIGE_PLATZHALTER else "")

_tel, _rg, _hrb = wert(TELEFON, "Telefonnummer"), wert(REGISTERGERICHT, "Amtsgericht"), wert(HRB, "HRB-Nummer")
_mail = f'<a href="mailto:{INFO_MAIL}">{INFO_MAIL}</a>'
IMP_ADRESSE = zeilen(wert(FIRMA, "Firmenname und Rechtsform"), wert(STRASSE, "Straße und Hausnummer"), wert(PLZ_ORT, "PLZ und Ort"))
IMP_KONTAKT = zeilen("Telefon: " + _tel if _tel else "", "E-Mail: " + _mail,
                     f'WhatsApp: <a {WA_ATTRS}>{WHATSAPP_ANZEIGE}</a>' if WHATSAPP_NUMBER else "")
IMP_REGISTER = ('<section><h2>Registereintrag</h2><p>' + zeilen("Eintragung im Handelsregister", "Registergericht: " + _rg if _rg else "",
                "Registernummer: " + _hrb if _hrb else "") + '</p></section>') if (_rg or _hrb) else ""
IMP_MSTV = zeilen(wert(GESCHAEFTSFUEHRER, "Name"), wert(STRASSE, "Straße und Hausnummer"), wert(PLZ_ORT, "PLZ und Ort"))
DS_VERANTWORTLICH = zeilen(wert(FIRMA, "Firmenname"), wert(STRASSE, "Straße und Hausnummer"), wert(PLZ_ORT, "PLZ und Ort"),
                           "Vertreten durch den Geschäftsführer " + wert(GESCHAEFTSFUEHRER, "Name"), "E-Mail: " + _mail)

impressum_body = f'''<section class="page-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Impressum</p>
    <h1 class="reveal">Impressum</h1>
  </div>
</section>
<section class="section" style="padding-top:0">
  <div class="wrap"><div class="legal">
    <!-- Firmendaten oben in build.py (FIRMA, GESCHAEFTSFUEHRER, STRASSE ...). Vor Veröffentlichung rechtlich prüfen lassen. -->
    {IMP_NOTE}
    <section><h2>Angaben gemäß § 5 DDG</h2><p>{IMP_ADRESSE}</p><p>Nexora ist ein Angebot der {wert(FIRMA, "Firmenname")}.</p></section>
    <section><h2>Vertreten durch</h2><p>Geschäftsführer: {wert(GESCHAEFTSFUEHRER, "Name der Geschäftsführung")}</p></section>
    <section><h2>Kontakt</h2><p>{IMP_KONTAKT}</p></section>
    {IMP_REGISTER}
    {IMP_UST}
    <section><h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2><p>{IMP_MSTV}</p></section>
  </div></div>
</section>
'''

datenschutz_body = f'''<section class="page-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Datenschutz</p>
    <h1 class="reveal">Datenschutz</h1>
  </div>
</section>
<section class="section" style="padding-top:0">
  <div class="wrap"><div class="legal">
    <!-- Entwurf auf Grundlage der tatsächlich genutzten Dienste. Vor dem Livegang von einer Fachperson oder einem Generator prüfen lassen. -->
    {DS_NOTE}
    <section><h2>1. Verantwortliche Stelle</h2><p>Verantwortlich für die Datenverarbeitung auf dieser Website ist:</p><p>{DS_VERANTWORTLICH}</p></section>
    <section><h2>2. Das Wichtigste in Kürze</h2><p>Wir verarbeiten personenbezogene Daten nur, soweit es für den Betrieb dieser Website, die Beantwortung Ihrer Anfragen, die Terminvereinbarung und Bewerbungsverfahren nötig ist. Analyse-, Tracking- oder Werbedienste setzen wir nicht ein. Personenbezogene Daten sind alle Angaben, mit denen Sie persönlich erkannt werden können, zum Beispiel Name, E-Mail-Adresse oder IP-Adresse.</p></section>
    <section><h2>3. Hosting und Server-Logfiles</h2><p>Diese Website wird bei Vercel Inc. (USA) gehostet. Die Seiten werden über das weltweite Servernetz von Vercel ausgeliefert, die Formulare auf Servern von Vercel in Frankfurt am Main verarbeitet. Bei jedem Aufruf verarbeitet Vercel technisch notwendige Daten wie IP-Adresse, Datum und Uhrzeit, die aufgerufene Seite, die zuvor besuchte Seite sowie Browser und Betriebssystem. Das ist nötig, um die Website auszuliefern und vor Angriffen zu schützen.</p><p>Rechtsgrundlage ist unser berechtigtes Interesse an einem sicheren und zuverlässigen Betrieb der Website (Art. 6 Abs. 1 lit. f DSGVO). Mit Vercel besteht ein Vertrag zur Auftragsverarbeitung. Soweit Daten in die USA übermittelt werden, stützt sich das auf den Angemessenheitsbeschluss der EU-Kommission zum EU-US Data Privacy Framework, soweit Vercel danach zertifiziert ist, und auf die Standardvertragsklauseln der EU-Kommission.</p></section>
    <section id="anfrage"><h2>4. Kontaktformular und E-Mail</h2><p>Wenn Sie uns über das Kontaktformular schreiben, verarbeiten wir Ihr Anliegen, Ihren Namen, Ihre E-Mail-Adresse und Ihre Nachricht sowie, falls angegeben, Unternehmen, Telefonnummer und Website. {FORM_DS} Auf dem Webserver wird nichts gespeichert. An die angegebene Adresse schicken wir automatisch eine Eingangsbestätigung. Schreiben Sie uns direkt per E-Mail, gilt das sinngemäß.</p><p>Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, wenn Ihre Anfrage einen Vertrag oder dessen Vorbereitung betrifft, und sonst unser berechtigtes Interesse an der Beantwortung von Anfragen (Art. 6 Abs. 1 lit. f DSGVO).</p><p>Zum Schutz vor Missbrauch enthält das Formular ein für Menschen unsichtbares Feld und misst, wie lange das Ausfüllen dauert. Außerdem merkt sich der Server kurzzeitig im Arbeitsspeicher, wie viele Anfragen von einer IP-Adresse kommen, um Massenanfragen zu begrenzen. Diese Angaben werden nicht dauerhaft gespeichert, Cookies werden dafür nicht verwendet.</p><p>Ihre Anfrage löschen wir, sobald sie erledigt ist und keine gesetzlichen Aufbewahrungspflichten entgegenstehen, etwa für Geschäftsbriefe (bis zu sechs Jahre) oder steuerlich relevante Unterlagen (bis zu zehn Jahre).</p></section>
    <section id="bewerbung"><h2>5. Bewerbungen</h2><p>Wenn Sie sich über unser Formular bewerben, verarbeiten wir Ihren Namen, Ihre E-Mail-Adresse, die gewünschte Stelle und Ihre Nachricht sowie, falls angegeben, Telefonnummer, einen Link zu Profil oder Portfolio und Ihren Lebenslauf. Die Bewerbung wird wie beim Kontaktformular über Vercel in Frankfurt am Main und per E-Mail über {MAIL_ANBIETER} an uns übermittelt und nicht auf dem Webserver gespeichert. Sie erhalten eine Eingangsbestätigung.</p><p>Rechtsgrundlage ist die Anbahnung eines Beschäftigungsverhältnisses (Art. 6 Abs. 1 lit. b DSGVO). Zugriff haben nur die Personen, die am Bewerbungsverfahren beteiligt sind. Kommt es zu einer Einstellung, nehmen wir Ihre Unterlagen in die Personalakte auf. Andernfalls löschen wir Ihre Bewerbung spätestens sechs Monate nach Abschluss des Verfahrens, außer Sie haben einer längeren Speicherung zugestimmt.</p></section>
    <section id="calendly"><h2>6. Terminbuchung über Calendly</h2><p>Für Beratungstermine nutzen wir Calendly, einen Dienst der Calendly LLC (USA). {CAL_DS} Wenn Sie einen Termin buchen, verarbeitet Calendly Ihre Eingaben wie Name, E-Mail-Adresse und den gewählten Termin und übermittelt sie an uns.</p><p>Rechtsgrundlage für die Buchung ist Art. 6 Abs. 1 lit. b DSGVO, für das Laden des Kalenders {CAL_RG}. Soweit Calendly Daten in den USA verarbeitet, stützt sich das auf den Angemessenheitsbeschluss zum EU-US Data Privacy Framework, soweit Calendly danach zertifiziert ist, und auf die Standardvertragsklauseln der EU-Kommission. Mehr dazu in der <a href="https://calendly.com/privacy" target="_blank" rel="noopener">Datenschutzerklärung von Calendly</a>.</p></section>
    <section><h2>7. Kontakt per WhatsApp</h2><p>Unsere WhatsApp-Buttons sind einfache Links. Eine Verbindung zu WhatsApp entsteht erst, wenn Sie darauf klicken. Ab dann gelten auch die Datenschutzbestimmungen von WhatsApp (WhatsApp Ireland Limited, Irland, ein Unternehmen der Meta-Gruppe), und WhatsApp kann Daten in die USA übermitteln. Wenn Sie uns schreiben, verarbeiten wir Ihre Telefonnummer, Ihren Profilnamen und Ihre Nachrichten, um Ihre Anfrage zu beantworten (Art. 6 Abs. 1 lit. b oder lit. f DSGVO). Möchten Sie WhatsApp nicht nutzen, erreichen Sie uns genauso per E-Mail oder über das Kontaktformular.</p></section>
    <section><h2>8. Cookies und Speicher im Browser</h2><p>{COOKIE_DS} Analyse- oder Werbe-Cookies verwenden wir nicht.</p></section>
    <section><h2>9. Schriftarten</h2><p>Die Schriftarten dieser Website sind lokal eingebunden. Beim Aufruf wird keine Verbindung zu Servern von Google hergestellt.</p></section>
    <section><h2>10. Verschlüsselung</h2><p>Diese Website nutzt aus Sicherheitsgründen eine TLS-Verschlüsselung. Eine verschlüsselte Verbindung erkennen Sie an „https://“ in der Adresszeile Ihres Browsers.</p></section>
    <section><h2>11. Ihre Rechte</h2><p>Sie haben jederzeit das Recht auf</p><ul><li>Auskunft über Ihre bei uns gespeicherten Daten (Art. 15 DSGVO)</li><li>Berichtigung unrichtiger Daten (Art. 16 DSGVO)</li><li>Löschung (Art. 17 DSGVO) und Einschränkung der Verarbeitung (Art. 18 DSGVO)</li><li>Datenübertragbarkeit (Art. 20 DSGVO)</li><li>Widerruf einer erteilten Einwilligung mit Wirkung für die Zukunft (Art. 7 Abs. 3 DSGVO)</li><li>Beschwerde bei einer Datenschutz-Aufsichtsbehörde (Art. 77 DSGVO)</li></ul><p><b>Widerspruchsrecht:</b> Verarbeiten wir Daten auf Grundlage unseres berechtigten Interesses (Art. 6 Abs. 1 lit. f DSGVO), können Sie dem aus Gründen, die sich aus Ihrer besonderen Situation ergeben, jederzeit widersprechen (Art. 21 DSGVO).</p><p>Für all das genügt eine formlose Nachricht an <a href="mailto:{INFO_MAIL}">{INFO_MAIL}</a>. Eine automatisierte Entscheidungsfindung einschließlich Profiling findet nicht statt.</p><p>Stand: {DS_STAND}</p></section>
  </div></div>
</section>
'''

page("impressum.html", "Impressum · Nexora", f"Impressum der Nexora Webagentur, ein Angebot der {FIRMA}.", "", impressum_body)
page("datenschutz.html", "Datenschutz · Nexora", "Datenschutzerklärung der Nexora Webagentur.", "", datenschutz_body)
print("built", FONT_MODE, sorted(p.name for p in OUT.glob("*.html")))


# ================= 404 =================
nf_body = f"""<section class="page-hero nf">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Start</a> / Fehler 404</p>
    <h1 class="reveal">Seite nicht <span class="grad-text">gefunden</span></h1>
    <p class="lede reveal" data-d="1">Diese Seite gibt es nicht oder nicht mehr. Vielleicht hilft Ihnen einer dieser Links weiter.</p>
    <div class="hero-actions reveal" data-d="2">
      <a class="btn btn--grad magnetic" href="index.html">Zur Startseite {ARR}</a>
      <a class="btn btn--ghost" href="leistungen.html">Leistungen &amp; Preise</a>
      <a class="btn btn--ghost" href="termin.html">Beratungstermin buchen</a>
    </div>
  </div>
</section>
"""
page("404.html", "Seite nicht gefunden · Nexora", "Diese Seite gibt es nicht oder nicht mehr.", "", nf_body, base=True, noindex=True)

# ================= Suchmaschinen =================
(OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n" + (f"\nSitemap: {SITE_URL}/sitemap.xml\n" if SITE_URL and LIVE else ""), encoding="utf-8")
if SITE_URL and LIVE:
    urls = "".join(f"  <url><loc>{SITE_URL}/{p}</loc></url>\n" for p in PAGES)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n', encoding="utf-8")
elif (OUT / "sitemap.xml").exists():
    (OUT / "sitemap.xml").unlink()

# ================= GitHub und Vercel =================
if FONT_MODE == "local" and FORM_BACKEND == "vercel":
    csp = "; ".join([
        "default-src 'self'",
        f"script-src 'self' '{HEAD_JS_HASH}'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-src https://calendly.com https://*.calendly.com",
        "form-action 'self'",
        "base-uri 'self'",
        "frame-ancestors 'self'",
        "object-src 'none'",
        "upgrade-insecure-requests",
    ])
    vercel = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "regions": ["fra1"],   # Formular-Funktionen laufen in Frankfurt (Standard wäre Washington)
        "headers": [
            {"source": "/(.*)", "headers": [
                {"key": "Content-Security-Policy", "value": csp},
                {"key": "X-Content-Type-Options", "value": "nosniff"},
                {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
                {"key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=(), browsing-topics=()"},
                {"key": "X-Frame-Options", "value": "SAMEORIGIN"},
            ] + ([] if LIVE else [{"key": "X-Robots-Tag", "value": "noindex"}])},
            {"source": "/fonts/(.+\\.woff2)", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
            {"source": "/assets/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=86400, stale-while-revalidate=604800"}]},
        ],
    }
    # Eine Adresse für alle: www.<domain> leitet auf <domain> um (oder umgekehrt, je nach SITE_URL)
    site_host = urlsplit(SITE_URL).hostname or "" if SITE_URL else ""
    other_host = (site_host[4:] if site_host.startswith("www.") else "www." + site_host) if site_host else ""
    if other_host:
        # "/(.*)" statt "/:path*": nur so greift die Regel auch für die Startseite "/" (wie bei den Headern unten)
        vercel["redirects"] = [{"source": "/(.*)", "has": [{"type": "host", "value": other_host}],
                                "destination": SITE_URL + "/$1", "permanent": True}]
    (OUT / "vercel.json").write_text(json.dumps(vercel, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pkg = {
        "name": "nexora-website",
        "private": True,
        "description": "Website der Nexora Webagentur: statische Seiten und Vercel-Funktionen für Bewerbungs- und Kontaktformular",
        "dependencies": {"nodemailer": "^10.6.0"},
    }
    (OUT / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / ".gitignore").write_text("node_modules/\n.vercel/\n.env*\n.DS_Store\n__pycache__/\n", encoding="utf-8")
    (OUT / ".vercelignore").write_text("_build/\nREADME.md\n", encoding="utf-8")
