/*
 * Nexora – Bewerbungsformular (Vercel Function, erreichbar unter /api/bewerbung)
 * Schickt jede Bewerbung als E-Mail an EMPFAENGER, mit dem Lebenslauf im Anhang,
 * und eine automatische Eingangsbestätigung an die Person, die sich bewirbt.
 * Auf dem Server wird nichts gespeichert.
 * Diese Datei entsteht beim Bauen aus _build/bewerbung.vercel.js und _build/formular-basis.js.
 *
 * Einstellungen in Vercel unter Settings > Environment Variables:
 *   SMTP_HOST   Postausgangsserver des Absender-Postfachs, z. B. smtp.ionos.de
 *   SMTP_PORT   465 (SSL, Standard) oder 587 (STARTTLS)
 *   SMTP_USER   Login des Absender-Postfachs, z. B. info@infonexora.de
 *   SMTP_PASS   Passwort dieses Postfachs
 *   MAIL_TO     optional: Postfach für alle Formulare, mehrere mit Komma getrennt (Standard hier: info@infonexora.de)
 *   MAIL_FROM   optional: Absenderadresse (Standard: SMTP_USER)
 */
"use strict";

// ================= EINSTELLUNGEN =================
const EMPFAENGER = process.env.MAIL_TO || "info@infonexora.de";
const ABSENDER_NAME = "Nexora Website";
const BESTAETIGUNG = true;        // Eingangsbestätigung an die Bewerberin / den Bewerber
const MAX_MB = 4;        // Vercel nimmt höchstens 4,5 MB pro Anfrage an
const MAX_PRO_STUNDE = 5;         // Schutz vor Missbrauch: Bewerbungen pro Anschluss und Stunde
const SEITE = "/bewerbung.html";  // Rückkehr, wenn das Formular ohne JavaScript abgeschickt wurde
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
    // Anker #gesendet / #fehler: ohne JavaScript zeigt das CSS (:target) die passende Meldung
    res.setHeader("Location", `${SEITE}?status=${ok ? "gesendet#gesendet" : "fehler#fehler"}`);
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

const STELLEN = { vertrieb: "Vertrieb (m/w/d)", developer: "Developer (m/w/d)", initiativ: "Initiativbewerbung" };
const KURZ = { vertrieb: "Vertrieb", developer: "Developer", initiativ: "Initiativ" };
const DANKE = { vertrieb: "deine Bewerbung für den Vertrieb", developer: "deine Bewerbung als Developer", initiativ: "deine Initiativbewerbung" };
const TYPEN = {
  pdf: "application/pdf",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
};
// Inhalt prüfen, nicht nur die Endung (erste Bytes der Datei)
const SIGNATUR = {
  pdf: b => b.subarray(0, 1024).includes(Buffer.from("%PDF")),
  doc: b => b.subarray(0, 8).equals(Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1])),
  docx: b => b.subarray(0, 4).equals(Buffer.from([0x50, 0x4b, 0x03, 0x04])),
  jpg: b => b.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff])),
  jpeg: b => b.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff])),
  png: b => b.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])),
};

module.exports = async function bewerbung(req, res) {
  if (req.method !== "POST") {
    res.statusCode = 303;
    res.setHeader("Location", SEITE);
    return res.end();
  }
  if (Number(req.headers["content-length"] || 0) > MAX_MB * 1048576 + 262144) {
    return antwort(req, res, false, `Die Datei ist zu groß. Bitte lade höchstens ${MAX_MB} MB hoch.`, 413);
  }

  let fd;
  try {
    fd = await formular(req);
  } catch (e) {
    return antwort(req, res, false, "Das Formular konnte nicht gelesen werden. Bitte versuch es noch einmal.", 400);
  }

  // Spamschutz: verstecktes Feld und Mindestdauer (Bots füllen alles in Sekunden aus)
  if (feld(fd, "firma").trim() !== "" || (fd.has("dauer") && Number(feld(fd, "dauer")) < 3)) {
    return antwort(req, res, true);
  }

  const schluessel = feld(fd, "stelle");
  const stelle = Object.hasOwn(STELLEN, schluessel) ? STELLEN[schluessel] : "";
  const name = zeile(feld(fd, "name"), 120);
  const email = feld(fd, "email").trim();
  const telefon = zeile(feld(fd, "telefon"), 40);
  const link = zeile(feld(fd, "link"), 300);
  const text = mehrzeilig(feld(fd, "nachricht"), 5000);

  if (!stelle) return antwort(req, res, false, "Bitte wähle eine Stelle aus.", 422);
  if (!name) return antwort(req, res, false, "Bitte gib deinen Namen ein.", 422);
  if (email.length > 160 || !EMAIL_OK.test(email)) {
    return antwort(req, res, false, "Bitte gib eine gültige E-Mail-Adresse ein.", 422);
  }
  if (link && !LINK_OK.test(link)) {
    return antwort(req, res, false, "Bitte gib einen vollständigen Link ein, zum Beispiel https://linkedin.com/in/…", 422);
  }
  if (feld(fd, "datenschutz") !== "ja") return antwort(req, res, false, "Bitte bestätige die Datenschutzhinweise.", 422);

  // Lebenslauf (optional)
  let anhang = null;
  const datei = fd.get("lebenslauf");
  if (datei && typeof datei === "object" && datei.size > 0) {
    if (datei.size > MAX_MB * 1048576) return antwort(req, res, false, `Die Datei ist größer als ${MAX_MB} MB.`, 413);
    const original = String(datei.name || "");
    const endung = (original.match(/\.([a-z0-9]+)$/i) || [])[1]?.toLowerCase() || "";
    if (!Object.hasOwn(TYPEN, endung)) return antwort(req, res, false, "Bitte lade eine PDF-, Word- oder Bilddatei hoch.", 415);
    const daten = Buffer.from(await datei.arrayBuffer());
    if (!SIGNATUR[endung](daten)) {
      return antwort(req, res, false, "Die Datei scheint beschädigt zu sein oder hat ein anderes Format. Bitte lade eine PDF-, Word- oder Bilddatei hoch.", 415);
    }
    const basis = original.replace(/\.[^.]*$/, "")
      .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/Ä/g, "Ae").replace(/Ö/g, "Oe").replace(/Ü/g, "Ue").replace(/ß/g, "ss")
      .replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
    anhang = { filename: `${basis || "Lebenslauf"}.${endung}`, content: daten, contentType: TYPEN[endung] };
  }

  if (zuViele(req)) {
    return antwort(req, res, false, "Von deinem Anschluss wurden gerade sehr viele Bewerbungen gesendet. Bitte versuch es später noch einmal.", 429);
  }

  const { datum, uhrzeit } = eingang();
  const nachricht = [
    "Neue Bewerbung über die Website",
    "",
    `Stelle:    ${stelle}`,
    `Name:      ${name}`,
    `E-Mail:    ${email}`,
    `Telefon:   ${telefon || "-"}`,
    `Profil:    ${link || "-"}`,
    `Anhang:    ${anhang ? anhang.filename : "kein Lebenslauf hochgeladen"}`,
    "",
    "Nachricht:",
    text || "-",
    "",
    "-- ",
    `Eingegangen am ${datum} um ${uhrzeit} Uhr über das Bewerbungsformular.`,
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
      subject: `Bewerbung ${KURZ[schluessel]}: ${name}`,
      text: nachricht,
      attachments: anhang ? [anhang] : [],
      headers: AUTOMATISCH,
    });
  } catch (e) {
    console.error("Bewerbung konnte nicht gesendet werden:", e.message);
    return antwort(req, res, false, "", 500);
  }

  if (BESTAETIGUNG) {
    const danke = [
      "Hallo,",
      "",
      `vielen Dank für ${DANKE[schluessel]} bei Nexora. Sie ist gut bei uns angekommen.`,
      "",
      "Wir schauen uns deine Angaben persönlich an und melden uns innerhalb weniger Tage bei dir.",
      "",
      "Viele Grüße",
      "Dein Nexora-Team",
      "",
      "-- ",
      "Diese E-Mail wurde automatisch verschickt. Bei Fragen antworte einfach auf diese Nachricht.",
    ].join("\n");
    try {
      await smtp.sendMail({ from: { name: "Nexora", address: von.address }, to: email, replyTo: { name: "Nexora", address: adressen(EMPFAENGER)[0] }, subject: "Deine Bewerbung bei Nexora", text: danke, headers: AUTOMATISCH });
    } catch (e) {
      console.error("Bestätigung konnte nicht gesendet werden:", e.message);
    }
  }

  return antwort(req, res, true);
};
