<?php
declare(strict_types=1);
/*
 * Nexora – Kontaktformular (kontakt.html), Variante für klassischen Webspace mit PHP
 * Schickt jede Anfrage als E-Mail an EMPFAENGER und auf Wunsch eine automatische
 * Eingangsbestätigung an die Person, die anfragt.
 * Voraussetzung: Hosting mit PHP 7.4 oder neuer und E-Mail-Versand über mail()
 * (Standard bei deutschen Hostern). Auf dem Server wird nichts gespeichert.
 */

// ================= EINSTELLUNGEN =================
const EMPFAENGER     = '__EMPFAENGER__';   // hier kommen die Anfragen an
const ABSENDER       = '';                 // leer = automatisch "website@<eure-domain>", sonst z. B. 'website@nexora.de'
const ABSENDER_NAME  = 'Nexora Website';
const BESTAETIGUNG   = true;               // Eingangsbestätigung an die anfragende Person
const ANTWORTZEIT    = '__ANTWORTZEIT__';
const WEBSITE        = '__SITE_URL__';     // für den Terminlink in der Bestätigung (leer = ohne Link)
const MAX_PRO_STUNDE = 5;                  // Schutz vor Missbrauch: Anfragen pro Anschluss und Stunde
// =================================================

date_default_timezone_set('Europe/Berlin');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

$json = strpos((string)($_SERVER['HTTP_ACCEPT'] ?? ''), 'application/json') !== false;

function antwort(bool $ok, string $fehler = '', int $code = 400): void
{
    global $json;
    if ($json) {
        http_response_code($ok ? 200 : $code);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($ok ? ['ok' => true] : ['ok' => false, 'error' => $fehler], JSON_UNESCAPED_UNICODE);
    } else {
        header('Location: kontakt.html?status=' . ($ok ? 'gesendet' : 'fehler'), true, 303);
    }
    exit;
}

function kuerzen(string $text, int $max): string
{
    return function_exists('mb_substr') ? (string)mb_substr($text, 0, $max, 'UTF-8') : substr($text, 0, $max);
}

function zeile($wert, int $max): string
{
    $wert = (string)preg_replace('/[\x00-\x1F\x7F]+/u', ' ', (string)$wert);
    return kuerzen(trim($wert), $max);
}

function kodiert(string $text): string
{
    return '=?UTF-8?B?' . base64_encode($text) . '?=';
}

function absender(): string
{
    if (ABSENDER !== '') {
        return ABSENDER;
    }
    $host = strtolower((string)($_SERVER['SERVER_NAME'] ?? ''));
    $host = (string)preg_replace('/^www\./', '', $host);
    if (!preg_match('/^[a-z0-9.-]+\.[a-z]{2,}$/', $host)) {
        $host = substr((string)strrchr(EMPFAENGER, '@'), 1);
    }
    return 'website@' . $host;
}

function senden(string $an, string $betreff, string $text, string $antwortAn, string $antwortName, string $vonName = ABSENDER_NAME): bool
{
    $von = absender();
    $kopf = implode("\r\n", [
        'From: ' . kodiert($vonName) . ' <' . $von . '>',
        'Reply-To: ' . ($antwortName !== '' ? kodiert($antwortName) . ' ' : '') . '<' . $antwortAn . '>',
        'Auto-Submitted: auto-generated',            // Autoresponder antworten nicht auf diese Mail
        'X-Auto-Response-Suppress: OOF, AutoReply',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: base64',
    ]);
    $inhalt = chunk_split(base64_encode($text));
    $ok = @mail($an, kodiert($betreff), $inhalt, $kopf, '-f' . $von);
    if (!$ok) {
        $ok = @mail($an, kodiert($betreff), $inhalt, $kopf);   // manche Hoster erlauben -f nicht
    }
    return $ok;
}

function zuViele(): bool
{
    $datei = sys_get_temp_dir() . '/nexora-anfrage-' . substr(hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . __FILE__), 0, 24);
    $jetzt = time();
    $zeiten = [];
    if (is_file($datei)) {
        foreach (explode(',', (string)@file_get_contents($datei)) as $t) {
            if ((int)$t > $jetzt - 3600) {
                $zeiten[] = (int)$t;
            }
        }
    }
    if (count($zeiten) >= MAX_PRO_STUNDE) {
        return true;
    }
    $zeiten[] = $jetzt;
    @file_put_contents($datei, implode(',', $zeiten), LOCK_EX);
    return false;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Location: kontakt.html', true, 303);
    exit;
}

// Spamschutz: verstecktes Feld und Mindestdauer (Bots füllen alles in Sekunden aus)
if (trim((string)($_POST['firma'] ?? '')) !== '' || (isset($_POST['dauer']) && (int)$_POST['dauer'] < 3)) {
    antwort(true);
}

$themen = ['kaufen' => 'Website kaufen', 'mieten' => 'Website mieten', 'betreuung' => 'Website-Betreuung', 'sonstiges' => 'Sonstiges'];
$danketext = [
    'kaufen'    => 'Ihre Anfrage zum Kauf einer Website',
    'mieten'    => 'Ihre Anfrage zur Website-Miete',
    'betreuung' => 'Ihre Anfrage zur Website-Betreuung',
    'sonstiges' => 'Ihre Anfrage',
];
$schluessel  = (string)($_POST['anliegen'] ?? '');
$anliegen    = $themen[$schluessel] ?? '';
$name        = zeile($_POST['name'] ?? '', 120);
$unternehmen = zeile($_POST['unternehmen'] ?? '', 120);
$email       = trim((string)($_POST['email'] ?? ''));
$telefon     = zeile($_POST['telefon'] ?? '', 40);
$website     = zeile($_POST['website'] ?? '', 300);
$text        = kuerzen(trim(str_replace(["\r\n", "\r"], "\n", (string)($_POST['nachricht'] ?? ''))), 5000);

if ($anliegen === '') {
    antwort(false, 'Bitte wählen Sie aus, worum es geht.', 422);
}
if ($name === '') {
    antwort(false, 'Bitte geben Sie Ihren Namen ein.', 422);
}
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    antwort(false, 'Bitte geben Sie eine gültige E-Mail-Adresse ein.', 422);
}
if ($website !== '' && !preg_match('~^https?://\S+\.\S+$~i', $website)) {
    antwort(false, 'Bitte geben Sie die vollständige Adresse ein, zum Beispiel https://ihre-firma.de', 422);
}
if ($text === '') {
    antwort(false, 'Bitte schreiben Sie uns kurz, worum es geht.', 422);
}
if (($_POST['datenschutz'] ?? '') !== 'ja') {
    antwort(false, 'Bitte bestätigen Sie die Datenschutzhinweise.', 422);
}
if (zuViele()) {
    antwort(false, 'Von Ihrem Anschluss wurden gerade sehr viele Anfragen gesendet. Bitte versuchen Sie es später noch einmal.', 429);
}

$nachricht = implode("\r\n", [
    'Neue Anfrage über die Website',
    '',
    'Anliegen:     ' . $anliegen,
    'Name:         ' . $name,
    'Unternehmen:  ' . ($unternehmen !== '' ? $unternehmen : '-'),
    'E-Mail:       ' . $email,
    'Telefon:      ' . ($telefon !== '' ? $telefon : '-'),
    'Website:      ' . ($website !== '' ? $website : '-'),
    '',
    'Nachricht:',
    str_replace("\n", "\r\n", $text),
    '',
    '-- ',
    'Eingegangen am ' . date('d.m.Y') . ' um ' . date('H:i') . ' Uhr über das Kontaktformular.',
    'Mit "Antworten" schreibst du direkt an ' . $name . '.',
]);

$betreff = 'Anfrage ' . $anliegen . ': ' . $name . ($unternehmen !== '' ? ' (' . $unternehmen . ')' : '');
if (!senden(EMPFAENGER, $betreff, $nachricht, $email, $name)) {
    antwort(false, '', 500);
}

// Die Bestätigung enthält bewusst nichts, was die Person selbst eingetippt hat.
if (BESTAETIGUNG) {
    $zeilen = [
        'Guten Tag,',
        '',
        'vielen Dank für ' . $danketext[$schluessel] . '. Sie ist gut bei uns angekommen.',
        '',
        'Wir sehen uns Ihr Anliegen persönlich an und melden uns ' . ANTWORTZEIT . ' bei Ihnen.',
    ];
    if (WEBSITE !== '') {
        array_push($zeilen, '', 'Wenn es schneller gehen soll, buchen Sie gern direkt einen kostenlosen Beratungstermin:', WEBSITE . '/termin.html');
    }
    array_push($zeilen, '', 'Viele Grüße', 'Ihr Nexora-Team', '', '-- ', 'Diese E-Mail wurde automatisch verschickt. Bei Fragen antworten Sie einfach auf diese Nachricht.');
    senden($email, 'Ihre Anfrage bei Nexora', implode("\r\n", $zeilen), EMPFAENGER, 'Nexora', 'Nexora');
}

antwort(true);
