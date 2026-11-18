// ----- Gemeinsame Bausteine beider Formulare (Quelle: _build/formular-basis.js, beim Bauen eingefügt) -----
const nodemailer = require("nodemailer");

const zeiten = new Map();   // Anfragen pro Anschluss (gilt je Server-Instanz)

const zeile = (wert, max) => String(wert ?? "").replace(/[\u0000-\u001f\u007f]+/g, " ").trim().slice(0, max);
const mehrzeilig = (wert, max) => String(wert ?? "").replace(/\r\n?/g, "\n").trim().slice(0, max);
const feld = (fd, name) => { const v = fd.get(name); return typeof v === "string" ? v : ""; };
const EMAIL_OK = /^[^\s@<>()[\]",;:\\]+@[^\s@<>()[\]",;:\\]+\.[^\s@<>()[\]",;:\\]{2,}$/;
const LINK_OK = /^https?:\/\/\S+\.\S+$/i;
// MAIL_TO darf mehrere Adressen enthalten, mit Komma getrennt (z. B. für zwei Personen)
const adressen = liste => String(liste).split(",").map(a => a.trim()).filter(Boolean);

// Kennzeichnet beide Mails als automatisch verschickt. So antworten Abwesenheitsnotizen
// und Autoresponder (im eigenen Postfach wie beim Absender) nicht noch einmal darauf.
const AUTOMATISCH = { "Auto-Submitted": "auto-generated", "X-Auto-Response-Suppress": "OOF, AutoReply" };

function antwort(req, res, ok, fehler = "", code = 400) {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Cache-Control", "no-store");
  if (String(req.headers.accept || "").includes("application/json")) {
    res.statusCode = ok ? 200 : code;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(ok ? { ok: true } : { ok: false, error: fehler }));
  } else {
    res.statusCode = 303;
    res.setHeader("Location", `${SEITE}?status=${ok ? "gesendet" : "fehler"}`);
    res.end();
  }
}

function zuViele(req) {
  const ip = String(req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "").split(",")[0].trim();
  const jetzt = Date.now();
  const liste = (zeiten.get(ip) || []).filter(t => t > jetzt - 3600e3);
  if (liste.length >= MAX_PRO_STUNDE) return true;
  liste.push(jetzt);
  zeiten.set(ip, liste);
  if (zeiten.size > 5000) zeiten.clear();
  return false;
}

const MAX_INHALT = 5 * 1048576;   // Obergrenze beim Einlesen (Vercel nimmt ohnehin höchstens 4,5 MB an)

async function formular(req) {
  // Inhalt über die Ereignisse data und end einlesen. Das klappt mit einer normalen Node-Anfrage und auch
  // auf Vercel: Dort liest die Laufzeit den Inhalt vorab und stellt ihn nur über diese Ereignisse erneut bereit.
  const inhalt = await new Promise((fertig, fehler) => {
    const teile = [];
    let groesse = 0;
    req.on("data", teil => {
      groesse += teil.length;
      if (groesse > MAX_INHALT) return fehler(new Error("Anfrage zu groß"));
      teile.push(teil);
    });
    req.on("end", () => fertig(Buffer.concat(teile)));
    req.on("error", fehler);
  });
  // Dann in eine Web-Anfrage umwandeln, die multipart/form-data und URL-kodierte Formulare selbst lesen kann
  const headers = new Headers();
  for (const [k, v] of Object.entries(req.headers)) if (v != null) headers.set(k, Array.isArray(v) ? v.join(", ") : String(v));
  headers.delete("content-length");
  headers.delete("transfer-encoding");
  const anfrage = new Request(`https://${req.headers.host || "localhost"}${req.url}`, { method: "POST", headers, body: inhalt });
  return anfrage.formData();
}

function versand() {
  // Klare Meldung in den Vercel-Logs, wenn der Mailversand noch nicht eingerichtet ist
  const fehlt = ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"].filter(k => !process.env[k]);
  if (fehlt.length) throw new Error(`Mailversand nicht eingerichtet, es fehlt: ${fehlt.join(", ")} (Vercel > Settings > Environment Variables, danach Redeploy)`);
  const port = Number(process.env.SMTP_PORT || 465);
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    secure: port === 465,          // 465: SSL, 587: STARTTLS
    requireTLS: port === 587,      // Passwort nie unverschlüsselt senden
    auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
    connectionTimeout: 10000,      // falscher Server: nach 10 s abbrechen statt hängen
    greetingTimeout: 10000,
    socketTimeout: 20000,
  });
}

function eingang() {
  const jetzt = new Date();
  return {
    datum: jetzt.toLocaleDateString("de-DE", { timeZone: "Europe/Berlin", day: "2-digit", month: "2-digit", year: "numeric" }),
    uhrzeit: jetzt.toLocaleTimeString("de-DE", { timeZone: "Europe/Berlin", hour: "2-digit", minute: "2-digit" }),
  };
}
// ----- Ende der gemeinsamen Bausteine -----
