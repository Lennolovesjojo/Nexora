/*
 * Nexora – Kontaktformular (Vercel Function, erreichbar unter /api/anfrage)
 * Schickt jede Anfrage als E-Mail an EMPFAENGER und eine automatische
 * Eingangsbestätigung an die Person, die anfragt. Auf dem Server wird nichts gespeichert.
 * Diese Datei entsteht beim Bauen aus _build/anfrage.vercel.js und _build/formular-basis.js.
 *
 * Einstellungen in Vercel unter Settings > Environment Variables (dieselben wie beim Bewerbungsformular):
 *   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS   Zugang zum Absender-Postfach
 *   MAIL_TO     optional: Postfach für alle Formulare, mehrere mit Komma getrennt (Standard hier: __EMPFAENGER__)
 *   MAIL_FROM   optional: Absenderadresse (Standard: SMTP_USER)
 */
"use strict";

// ================= EINSTELLUNGEN =================
const EMPFAENGER = process.env.MAIL_TO || "__EMPFAENGER__";
const ABSENDER_NAME = "Nexora Website";
const BESTAETIGUNG = true;        // Eingangsbestätigung an die anfragende Person
const ANTWORTZEIT = "__ANTWORTZEIT__";
const WEBSITE = "__SITE_URL__";   // für den Terminlink in der Bestätigung (leer = ohne Link)
const MAX_PRO_STUNDE = 5;         // Schutz vor Missbrauch: Anfragen pro Anschluss und Stunde
const SEITE = "/kontakt.html";    // Rückkehr, wenn das Formular ohne JavaScript abgeschickt wurde
// =================================================

/*__BASIS__*/

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
