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
 *   MAIL_TO     optional: Postfach für alle Formulare, mehrere mit Komma getrennt (Standard hier: __EMPFAENGER__)
 *   MAIL_FROM   optional: Absenderadresse (Standard: SMTP_USER)
 */
"use strict";

// ================= EINSTELLUNGEN =================
const EMPFAENGER = process.env.MAIL_TO || "__EMPFAENGER__";
const ABSENDER_NAME = "Nexora Website";
const BESTAETIGUNG = true;        // Eingangsbestätigung an die Bewerberin / den Bewerber
const MAX_MB = __MAX_MB__;        // Vercel nimmt höchstens 4,5 MB pro Anfrage an
const MAX_PRO_STUNDE = 5;         // Schutz vor Missbrauch: Bewerbungen pro Anschluss und Stunde
const SEITE = "/bewerbung.html";  // Rückkehr, wenn das Formular ohne JavaScript abgeschickt wurde
// =================================================

/*__BASIS__*/

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
