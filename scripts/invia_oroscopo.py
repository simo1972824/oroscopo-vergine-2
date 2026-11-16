import os
import smtplib
import ssl
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


def excerpt(html, weekday, limit=2200):
    text = page_text(html)
    idx = text.lower().find(weekday)
    if idx > 0:
        text = text[idx:]
    return text[:limit]


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


def main():
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    now = datetime.now(ROME)
    if not manual and now.hour != 6:
        print(f"Skip: ora di Roma {now:%H:%M}, invio previsto solo alle 06:00")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
