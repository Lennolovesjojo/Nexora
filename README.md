# Nexora Website

Die Website der Nexora Webagentur: neun statische Seiten, eine 404-Seite und zwei kleine
Vercel-Funktionen, die das Bewerbungs- und das Kontaktformular per E-Mail verschicken.

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `index.html`, `leistungen.html`, `ueber-uns.html`, `karriere.html`, `termin.html`, `kontakt.html`, `bewerbung.html`, `impressum.html`, `datenschutz.html`, `404.html` | die Seiten (werden von `_build/build.py` erzeugt) |
| `styles.css`, `main.js` | Gestaltung und Interaktionen (direkt bearbeiten) |
| `assets/` | Logos, Favicons, Vorschaubild für WhatsApp, LinkedIn und Co. (`og-image.jpg`), Teamfotos in `assets/team/` |
| `fonts/` | Schriften, lokal eingebunden (keine Verbindung zu Google) |
| `api/bewerbung.js`, `api/anfrage.js` | Vercel-Funktionen für Bewerbungs- und Kontaktformular |
| `vercel.json` | Sicherheits- und Cache-Header, Serverregion Frankfurt (`fra1`) |
| `package.json`, `package-lock.json` | Paket für den Mailversand der Formulare (nodemailer), in fester Version |
| `_build/` | `build.py` (Texte und Einstellungen) und Vorlagen. Wird nicht veröffentlicht. |

## Veröffentlichen

Die Website läuft auf Vercel im Team „Nexora“ (Pro-Tarif), Projekt `nexora-website`, Serverregion
Frankfurt. Bis die eigene Domain verbunden ist, ist sie unter
https://nexora-website-iota-ivory.vercel.app erreichbar. Vercel ist mit diesem Repository verbunden:

- Jeder Push auf `main` geht automatisch online.
- Jeder andere Branch und jeder Pull Request bekommt eine eigene Vorschau-Adresse,
  die Live-Seite bleibt dabei unverändert.

Eine Änderung läuft deshalb immer gleich: Texte und Einstellungen in `_build/build.py` ändern,
Gestaltung direkt in `styles.css` und `main.js`. Dann `python3 _build/build.py` ausführen und die
erzeugten Dateien mit committen. Die HTML-Seiten, `api/*.js`, `vercel.json`, `package.json`,
`robots.txt`, `.gitignore` und `.vercelignore` entstehen beim Bauen und werden nicht von Hand geändert.
`package-lock.json` legt die Version von nodemailer fest, damit jeder Deploy dieselbe nutzt.

### Einmalig in Vercel

1. Unter **Settings > Environment Variables** eintragen (Postfach, das die Formular-Mails verschickt):

   | Name | Beispiel |
   | --- | --- |
   | `SMTP_HOST` | `smtp.ionos.de` (steht beim E-Mail-Anbieter) |
   | `SMTP_PORT` | `465` |
   | `SMTP_USER` | `website@nexora.de` |
   | `SMTP_PASS` | Passwort dieses Postfachs |
   | `MAIL_TO` | optional: Postfach für beide Formulare, z. B. `info@nexora.de` (mehrere mit Komma getrennt) |

   Ohne `MAIL_TO` gehen Bewerbungen an `CAREER_MAIL` und Anfragen an `INFO_MAIL` (siehe unten).
   Solange die eigene Domain fehlt, geht auch ein bestehendes Postfach: dessen Zugangsdaten in `SMTP_*`,
   die Empfängeradresse in `MAIL_TO`.
   Danach unter **Deployments** einmal **Redeploy**, damit die Werte gelten.
2. Unter **Settings > Domains** die eigene Domain verbinden.
3. Je eine Testbewerbung und eine Testanfrage abschicken: Beide müssen im Postfach ankommen,
   die Bestätigungen beim Absender. Kommt nichts an, steht der Grund in Vercel unter **Logs**
   (Suche: „konnte nicht gesendet werden“), zum Beispiel welche Variable fehlt.

Muss das Projekt einmal neu angelegt werden: In Vercel **Add New > Project**, dieses Repository
importieren, Framework Preset **Other**, Build Command und Output Directory leer lassen.
Der kostenlose Hobby-Tarif ist nur für private, nicht kommerzielle Projekte erlaubt.

Ohne Vercel geht es auch: In `_build/build.py` `FORM_BACKEND = "php"` setzen und neu bauen.
Dann entstehen `bewerbung.php` und `anfrage.php` für klassischen Webspace mit PHP.

## Inhalte ändern

Texte, Preise, Team, Stellen und Einstellungen stehen in `_build/build.py`. Danach neu bauen
(Python 3.9 oder neuer, keine Zusatzpakete nötig):

```
python3 _build/build.py
```

Wichtige Einstellungen oben in `build.py`:

- `LIVE`: `False` ist der Testmodus. Suchmaschinen werden gebeten, nichts aufzunehmen (noindex),
  damit der Testlink nicht bei Google landet. Erst auf `True` setzen, wenn die Domain verbunden ist.
- `INFO_MAIL`, `CAREER_MAIL`: E-Mail-Adressen
- `SITE_URL`: Domain der fertigen Seite, z. B. `https://www.nexora.de`. Mit `LIVE = True` entstehen
  daraus Canonical-Links und `sitemap.xml`.
- `ANTWORTZEIT`: was die Bestätigungsmail zum Kontaktformular verspricht
- `WHATSAPP_NUMBER`, `WHATSAPP_TEXT`: WhatsApp Business
- `CALENDLY`, `CALENDLY_CONSENT`: Buchungskalender, und ob er erst nach Klick lädt
- `TEAM`: Profile. Fotos quadratisch und mit dem Gesicht in der Mitte als
  `assets/team/vorname-nachname.jpg` ablegen (z. B. `linus-schoeller.jpg`, Umlaute ohne Punkte).
  Beim Bauen werden sie automatisch erkannt, ohne Foto erscheinen die Initialen.

## Vor dem Livegang ersetzen

- Impressum und Datenschutzerklärung (gelb markierte Platzhalter)
- Zahlen (14 Tage, 99,9 %, 4,9 von 5, PageSpeed) und die acht Beispiel-Kundenstimmen
- E-Mail-Adressen, falls die Domain nicht `nexora.de` ist
- `LIVE = True` und `SITE_URL` setzen, dann neu bauen
