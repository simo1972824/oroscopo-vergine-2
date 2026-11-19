import os
import smtplib
import ssl
import subprocess
import sys
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
DAYS = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

DISCLAIMER = ("L'astologia è una forma di intrattenimento e non sostituisce "
              "il parere di professionisti (medici, legali, finanziari).")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header", "form"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header", "form") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)


def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9",
    })
    with urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", "replace")


def page_text(html):
    parser = TextExtractor()
    parser.feed(html)
    return " ".join(parser.parts)


END_MARKERS = ("tutti i segni", "ultimi pubblicati", "oroscopo della settimana",
               "oroscopo di oggi", "oroscopo di domani")


def excerpt(html, weekday, limit=1800):
    text = page_text(html)
    low = text.lower()
    idx = low.find(weekday)
    if idx > 0:
        text = text[idx:]
        low = text.lower()
    end = len(text)
    for marker in END_MARKERS:
        pos = low.find(marker, 250)
        if pos != -1 and pos < end:
            end = pos
    return text[:min(limit, end)].strip()


def build_sources(day):
    slug = f"{day.day:02d}-{day.month:02d}-{day.year}"
    return [
        ("Style Corriere", f"https://style.corriere.it/oroscopo/giorno/vergine-{slug}/"),
        ("Amica", f"https://www.amica.it/oroscopo/giorno/vergine-{slug}/"),
        ("Oggi.it", "https://www.oggi.it/oroscopo/oroscopo-di-oggi/vergine/"),
    ]


def compose_body(label, weekday, sources, excerpts):
    lines = [f"Ciao Simone!", "",
             f"Ecco l'oroscopo della VERGINE di oggi, {label}:", ""]
    if excerpts:
        for (name, url), text in zip(sources, excerpts):
            lines += [f"== {name} ==", text, ""]
    else:
        lines += ["Oggi non sono riuscito a recuperare il testo delle previsioni, "
                  "ecco i link diretti:", ""]
    lines += ["Fonti:"]
    for name, url in sources:
        lines.append(f"- {name}: {url}")
    lines += ["", "---", DISCLAIMER, "",
              "A domani con il nuovo oroscopo! ♍", "AstroVibe"]
    return "\n".join(lines)


MARKER = ".ultimo-invio.txt"


def read_marker():
    try:
        with open(MARKER, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def push_marker(date_str):
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("Marker non pushato: GITHUB_TOKEN/GITHUB_REPOSITORY mancanti")
        return
    with open(MARKER, "w", encoding="utf-8") as fh:
        fh.write(date_str + "\n")
    remote = f"https://x-access-token:{token}@github.com/{repo}.git"
    subprocess.run(["git", "remote", "set-url", "origin", remote], check=False)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=False)
    subprocess.run(["git", "config", "user.name", "github-actions"], check=False)
    subprocess.run(["git", "add", MARKER], check=False)
    subprocess.run(["git", "commit", "-m", f"chore: marker invio oroscopo {date_str}"], check=False)
    subprocess.run(["git", "push", "origin", "HEAD"], check=False)


def main():
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    now = datetime.now(ROME)
    today = now.date().isoformat()
    if not manual and read_marker() == today:
        print(f"Skip: oroscopo del {today} già inviato oggi")
        return 0

    weekday = DAYS[now.weekday()]
    label = f"{weekday} {now.day} {MONTHS[now.month - 1]} {now.year}"
    sources = build_sources(now)

    excerpts = []
    for name, url in sources:
        try:
            text = excerpt(fetch(url), weekday)
            excerpts.append(text)
            print(f"OK {name} ({len(text)} caratteri)")
        except Exception as exc:
            print(f"FAIL {name}: {exc}")

    user = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    recipient = os.environ.get("MAIL_TO", "").strip() or user
    if not user or not password:
        print("ERRORE: secret GMAIL_USER / GMAIL_APP_PASSWORD mancanti o vuoti")
        return 2

    subject = f"♍ Oroscopo Vergine di oggi — {label}"
    body = compose_body(label, weekday, sources, excerpts)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = user
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
        server.login(user, password)
        server.send_message(msg)
    print(f"Email inviata a {recipient}")
    push_marker(today)
    return 0


if __name__ == "__main__":
    sys.exit(main())
