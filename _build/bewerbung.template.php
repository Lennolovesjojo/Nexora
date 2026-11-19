<?php
declare(strict_types=1);
/*
 * Nexora – Bewerbungsformular (bewerbung.html)
 * Schickt jede Bewerbung als E-Mail an EMPFAENGER, mit dem Lebenslauf im Anhang,
 * und auf Wunsch eine automatische Eingangsbestätigung an die Person, die sich bewirbt.
 * Voraussetzung: Hosting mit PHP 7.4 oder neuer und E-Mail-Versand über mail()
 * (Standard bei deutschen Hostern). Auf dem Server wird nichts gespeichert.
 */

// ================= EINSTELLUNGEN =================
const EMPFAENGER    = '__EMPFAENGER__';   // hier kommen die Bewerbungen an
const ABSENDER      = '';                 // leer = automatisch "website@<eure-domain>", sonst z. B. 'website@nexora.de'
const ABSENDER_NAME = 'Nexora Website';
const BESTAETIGUNG  = true;               // Eingangsbestätigung an die Bewerberin / den Bewerber
const MAX_MB        = 10;                 // maximale Dateigröße für den Lebenslauf
const MAX_PRO_STUNDE = 5;                 // Schutz vor Missbrauch: Bewerbungen pro Anschluss und Stunde
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
        header('Location: bewerbung.html?status=' . ($ok ? 'gesendet#gesendet' : 'fehler#fehler'), true, 303);
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

function senden(string $an, string $betreff, string $text, string $antwortAn, string $antwortName, ?array $anhang = null, string $vonName = ABSENDER_NAME): bool
{
    $von = absender();
    $kopf = [
        'From: ' . kodiert($vonName) . ' <' . $von . '>',
        'Reply-To: ' . ($antwortName !== '' ? kodiert($antwortName) . ' ' : '') . '<' . $antwortAn . '>',
        'Auto-Submitted: auto-generated',            // Autoresponder antworten nicht auf diese Mail
        'X-Auto-Response-Suppress: OOF, AutoReply',
        'MIME-Version: 1.0',
    ];
    if ($anhang) {
        $grenze = 'nexora-' . bin2hex(random_bytes(12));
        $kopf[] = 'Content-Type: multipart/mixed; boundary="' . $grenze . '"';
        $inhalt = "--$grenze\r\n"
            . "Content-Type: text/plain; charset=UTF-8\r\n"
            . "Content-Transfer-Encoding: base64\r\n\r\n"
            . chunk_split(base64_encode($text)) . "\r\n"
            . "--$grenze\r\n"
            . 'Content-Type: ' . $anhang['typ'] . '; name="' . $anhang['name'] . "\"\r\n"
            . 'Content-Disposition: attachment; filename="' . $anhang['name'] . "\"\r\n"
            . "Content-Transfer-Encoding: base64\r\n\r\n"
            . chunk_split(base64_encode($anhang['daten'])) . "\r\n"
            . "--$grenze--\r\n";
    } else {
        $kopf[] = 'Content-Type: text/plain; charset=UTF-8';
        $kopf[] = 'Content-Transfer-Encoding: base64';
        $inhalt = chunk_split(base64_encode($text));
    }
    $kopfText = implode("\r\n", $kopf);
    $ok = @mail($an, kodiert($betreff), $inhalt, $kopfText, '-f' . $von);
    if (!$ok) {
        $ok = @mail($an, kodiert($betreff), $inhalt, $kopfText);   // manche Hoster erlauben -f nicht
    }
    return $ok;
}

function zuViele(): bool
{
    $datei = sys_get_temp_dir() . '/nexora-bewerbung-' . substr(hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . __FILE__), 0, 24);
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
    header('Location: bewerbung.html', true, 303);
    exit;
}
if (empty($_POST) && (int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 0) {
    antwort(false, 'Die Datei ist zu groß. Bitte lade höchstens ' . MAX_MB . ' MB hoch.', 413);
}

// Spamschutz: verstecktes Feld und Mindestdauer (Bots füllen alles in Sekunden aus)
if (trim((string)($_POST['firma'] ?? '')) !== '' || (isset($_POST['dauer']) && (int)$_POST['dauer'] < 3)) {
    antwort(true);
}

$stellen = ['vertrieb' => 'Vertrieb (m/w/d)', 'developer' => 'Developer (m/w/d)', 'initiativ' => 'Initiativbewerbung'];
$kurz    = ['vertrieb' => 'Vertrieb', 'developer' => 'Developer', 'initiativ' => 'Initiativ'];
$danketext = ['vertrieb' => 'deine Bewerbung für den Vertrieb', 'developer' => 'deine Bewerbung als Developer', 'initiativ' => 'deine Initiativbewerbung'];
$schluessel = (string)($_POST['stelle'] ?? '');
$stelle  = $stellen[$schluessel] ?? '';
$name    = zeile($_POST['name'] ?? '', 120);
$email   = trim((string)($_POST['email'] ?? ''));
$telefon = zeile($_POST['telefon'] ?? '', 40);
$link    = zeile($_POST['link'] ?? '', 300);
$text    = kuerzen(trim(str_replace(["\r\n", "\r"], "\n", (string)($_POST['nachricht'] ?? ''))), 5000);

if ($stelle === '') {
    antwort(false, 'Bitte wähle eine Stelle aus.', 422);
}
if ($name === '') {
    antwort(false, 'Bitte gib deinen Namen ein.', 422);
}
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    antwort(false, 'Bitte gib eine gültige E-Mail-Adresse ein.', 422);
}
if ($link !== '' && !preg_match('~^https?://\S+\.\S+$~i', $link)) {
    antwort(false, 'Bitte gib einen vollständigen Link ein, zum Beispiel https://linkedin.com/in/…', 422);
}
if (($_POST['datenschutz'] ?? '') !== 'ja') {
    antwort(false, 'Bitte bestätige die Datenschutzhinweise.', 422);
}

// Lebenslauf (optional)
$anhang = null;
$datei = $_FILES['lebenslauf'] ?? null;
if (is_array($datei) && ($datei['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_NO_FILE) {
    if (in_array($datei['error'], [UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE], true) || $datei['size'] > MAX_MB * 1048576) {
        antwort(false, 'Die Datei ist größer als ' . MAX_MB . ' MB.', 413);
    }
    if ($datei['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($datei['tmp_name'])) {
        antwort(false, 'Die Datei konnte nicht hochgeladen werden. Bitte versuch es noch einmal.', 400);
    }
    $typen = [
        'pdf'  => 'application/pdf',
        'doc'  => 'application/msword',
        'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'jpg'  => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'png'  => 'image/png',
    ];
    $endung = strtolower(pathinfo((string)$datei['name'], PATHINFO_EXTENSION));
    if (!isset($typen[$endung])) {
        antwort(false, 'Bitte lade eine PDF-, Word- oder Bilddatei hoch.', 415);
    }
    if (class_exists('finfo')) {   // Inhalt prüfen, nicht nur die Endung
        $echt = (string)(new finfo(FILEINFO_MIME_TYPE))->file($datei['tmp_name']);
        $passend = [
            'pdf'  => ['application/pdf'],
            'jpg'  => ['image/jpeg'],
            'jpeg' => ['image/jpeg'],
            'png'  => ['image/png'],
            'doc'  => ['application/msword', 'application/x-ole-storage', 'application/CDFV2', 'application/vnd.ms-office', 'application/octet-stream'],
            'docx' => ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip', 'application/octet-stream'],
        ];
        if (!in_array($echt, $passend[$endung], true)) {
            antwort(false, 'Die Datei scheint beschädigt zu sein oder hat ein anderes Format. Bitte lade eine PDF-, Word- oder Bilddatei hoch.', 415);
        }
    }
    $basis = strtr(pathinfo((string)$datei['name'], PATHINFO_FILENAME), ['ä' => 'ae', 'ö' => 'oe', 'ü' => 'ue', 'Ä' => 'Ae', 'Ö' => 'Oe', 'Ü' => 'Ue', 'ß' => 'ss']);
    $basis = trim((string)preg_replace('/[^A-Za-z0-9_-]+/', '-', $basis), '-');
    $anhang = [
        'name'  => substr($basis !== '' ? $basis : 'Lebenslauf', 0, 60) . '.' . $endung,
        'typ'   => $typen[$endung],
        'daten' => (string)file_get_contents($datei['tmp_name']),
    ];
}

if (zuViele()) {
    antwort(false, 'Von deinem Anschluss wurden gerade sehr viele Bewerbungen gesendet. Bitte versuch es später noch einmal.', 429);
}

$nachricht = implode("\r\n", [
    'Neue Bewerbung über die Website',
    '',
    'Stelle:    ' . $stelle,
    'Name:      ' . $name,
    'E-Mail:    ' . $email,
    'Telefon:   ' . ($telefon !== '' ? $telefon : '-'),
    'Profil:    ' . ($link !== '' ? $link : '-'),
    'Anhang:    ' . ($anhang ? $anhang['name'] : 'kein Lebenslauf hochgeladen'),
    '',
    'Nachricht:',
    $text !== '' ? str_replace("\n", "\r\n", $text) : '-',
    '',
    '-- ',
    'Eingegangen am ' . date('d.m.Y') . ' um ' . date('H:i') . ' Uhr über das Bewerbungsformular.',
    'Mit "Antworten" schreibst du direkt an ' . $name . '.',
]);

if (!senden(EMPFAENGER, 'Bewerbung ' . $kurz[$schluessel] . ': ' . $name, $nachricht, $email, $name, $anhang)) {
    antwort(false, '', 500);
}

if (BESTAETIGUNG) {
    $danke = implode("\r\n", [
        'Hallo,',
        '',
        'vielen Dank für ' . $danketext[$schluessel] . ' bei Nexora. Sie ist gut bei uns angekommen.',
        '',
        'Wir schauen uns deine Angaben persönlich an und melden uns innerhalb weniger Tage bei dir.',
        '',
        'Viele Grüße',
        'Dein Nexora-Team',
        '',
        '-- ',
        'Diese E-Mail wurde automatisch verschickt. Bei Fragen antworte einfach auf diese Nachricht.',
    ]);
    senden($email, 'Deine Bewerbung bei Nexora', $danke, EMPFAENGER, 'Nexora', null, 'Nexora');
}

antwort(true);
