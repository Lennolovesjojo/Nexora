/*
 * Nexora – Kontaktformular (Vercel Function, erreichbar unter /api/anfrage)
 * Schickt jede Anfrage als E-Mail an EMPFAENGER und eine automatische
 * Eingangsbestätigung an die Person, die anfragt. Auf dem Server wird nichts gespeichert.
 * Diese Datei entsteht beim Bauen aus _build/anfrage.vercel.js und _build/formular-basis.js.
 *
 * Einstellungen in Vercel unter Settings > Environment Variables (dieselben wie beim Bewerbungsformular):
 *   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS   Zugang zum Absender-Postfach
 *   MAIL_TO     optional: Postfach für alle Formulare, mehrere mit Komma getrennt (Standard hier: info@nexora.de)
 *   MAIL_FROM   optional: Absenderadresse (Standard: SMTP_USER)
 */
"use strict";

// ================= EINSTELLUNGEN =================
const EMPFAENGER = process.env.MAIL_TO || "info@nexora.de";
const ABSENDER_NAME = "Nexora Website";
const BESTAETIGUNG = true;        // Eingangsbestätigung an die anfragende Person
const ANTWORTZEIT = "in der Regel innerhalb eines Werktags";
const WEBSITE = "";   // für den Terminlink in der Bestätigung (leer = ohne Link)
const MAX_PRO_STUNDE = 5;         // Schutz vor Missbrauch: Anfragen pro Anschluss und Stunde
const SEITE = "/kontakt.html";    // Rückkehr, wenn das Formular ohne JavaScript abgeschickt wurde
// =================================================

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

const ANLIEGEN = { kaufen: "Website kaufen", mieten: "Website mieten", betreuung: "Website-Betreuung", sonstiges: "Sonstiges" };
const DANKE = {
  kaufen: "Ihre Anfrage zum Kauf einer Website",
  mieten: "Ihre Anfrage zur Website-Miete",
  betreuung: "Ihre Anfrage zur Website-Betreuung",
  sonstiges: "Ihre Anfrage",
};

module.exports = async function anfrage(req, res) {
  if (req.method !== "POST") {
    res.statusCode = 303;
    res.setHeader("Location", SEITE);
    return res.end();
  }
  if (Number(req.headers["content-length"] || 0) > 262144) {
    return antwort(req, res, false, "Die Nachricht ist zu lang. Bitte kürzen Sie sie etwas.", 413);
  }

  let fd;
  try {
    fd = await formular(req);
  } catch (e) {
    return antwort(req, res, false, "Das Formular konnte nicht gelesen werden. Bitte versuchen Sie es noch einmal.", 400);
  }

  // Spamschutz: verstecktes Feld und Mindestdauer (Bots füllen alles in Sekunden aus)
  if (feld(fd, "firma").trim() !== "" || (fd.has("dauer") && Number(feld(fd, "dauer")) < 3)) {
    return antwort(req, res, true);
  }

  const schluessel = feld(fd, "anliegen");
  const anliegen = Object.hasOwn(ANLIEGEN, schluessel) ? ANLIEGEN[schluessel] : "";
  const name = zeile(feld(fd, "name"), 120);
  const unternehmen = zeile(feld(fd, "unternehmen"), 120);
  const email = feld(fd, "email").trim();
  const telefon = zeile(feld(fd, "telefon"), 40);
  const website = zeile(feld(fd, "website"), 300);
  const text = mehrzeilig(feld(fd, "nachricht"), 5000);

  if (!anliegen) return antwort(req, res, false, "Bitte wählen Sie aus, worum es geht.", 422);
  if (!name) return antwort(req, res, false, "Bitte geben Sie Ihren Namen ein.", 422);
  if (email.length > 160 || !EMAIL_OK.test(email)) {
    return antwort(req, res, false, "Bitte geben Sie eine gültige E-Mail-Adresse ein.", 422);
  }
  if (website && !LINK_OK.test(website)) {
    return antwort(req, res, false, "Bitte geben Sie die vollständige Adresse ein, zum Beispiel https://ihre-firma.de", 422);
  }
  if (!text) return antwort(req, res, false, "Bitte schreiben Sie uns kurz, worum es geht.", 422);
  if (feld(fd, "datenschutz") !== "ja") return antwort(req, res, false, "Bitte bestätigen Sie die Datenschutzhinweise.", 422);

  if (zuViele(req)) {
    return antwort(req, res, false, "Von Ihrem Anschluss wurden gerade sehr viele Anfragen gesendet. Bitte versuchen Sie es später noch einmal.", 429);
  }

  const { datum, uhrzeit } = eingang();
  const nachricht = [
    "Neue Anfrage über die Website",
    "",
    `Anliegen:     ${anliegen}`,
    `Name:         ${name}`,
    `Unternehmen:  ${unternehmen || "-"}`,
    `E-Mail:       ${email}`,
    `Telefon:      ${telefon || "-"}`,
    `Website:      ${website || "-"}`,
    "",
    "Nachricht:",
    text,
    "",
    "-- ",
    `Eingegangen am ${datum} um ${uhrzeit} Uhr über das Kontaktformular.`,
    `Mit "Antworten" schreibst du direkt an ${name}.`,
  ].join("\n");

  let smtp;
  const von = { name: ABSENDER_NAME, address: process.env.MAIL_FROM || process.env.SMTP_USER };
  try {
    smtp = versand();
    await smtp.sendMail({
      from: von,
      to: adressen(EMPFAENGER),
      replyTo: { name, address: email },
      subject: `Anfrage ${anliegen}: ${name}${unternehmen ? ` (${unternehmen})` : ""}`,
      text: nachricht,
      headers: AUTOMATISCH,
    });
  } catch (e) {
    console.error("Anfrage konnte nicht gesendet werden:", e.message);
    return antwort(req, res, false, "", 500);
  }

  // Die Bestätigung enthält bewusst nichts, was die Person selbst eingetippt hat.
  // So lässt sich das Formular nicht missbrauchen, um fremden Text an fremde Adressen zu schicken.
  if (BESTAETIGUNG) {
    const termin = WEBSITE ? `${WEBSITE}/termin.html` : "";
    const danke = [
      "Guten Tag,",
      "",
      `vielen Dank für ${DANKE[schluessel]}. Sie ist gut bei uns angekommen.`,
      "",
      `Wir sehen uns Ihr Anliegen persönlich an und melden uns ${ANTWORTZEIT} bei Ihnen.`,
      ...(termin ? ["", "Wenn es schneller gehen soll, buchen Sie gern direkt einen kostenlosen Beratungstermin:", termin] : []),
      "",
      "Viele Grüße",
      "Ihr Nexora-Team",
      "",
      "-- ",
      "Diese E-Mail wurde automatisch verschickt. Bei Fragen antworten Sie einfach auf diese Nachricht.",
    ].join("\n");
    try {
      await smtp.sendMail({ from: { name: "Nexora", address: von.address }, to: email, replyTo: { name: "Nexora", address: adressen(EMPFAENGER)[0] }, subject: "Ihre Anfrage bei Nexora", text: danke, headers: AUTOMATISCH });
    } catch (e) {
      console.error("Bestätigung konnte nicht gesendet werden:", e.message);
    }
  }

  return antwort(req, res, true);
};
