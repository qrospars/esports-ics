"""Fetch the esportscalendar.app feed and rewrite it so Outlook accepts it.

Fixes: one URL per event (the source sends two), lines folded at 75 octets,
unescaped commas/semicolons in text, and past events dropped to keep it small.
"""
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

SOURCE = os.environ.get("SOURCE_URL", "https://esportscalendar.app/369cc831ee677b3c.ics")
KEEP_DAYS_BACK = int(os.environ.get("KEEP_DAYS_BACK", "7"))
OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/calendar.ics"
TEXT_PROPS = {"SUMMARY", "DESCRIPTION", "LOCATION"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "esports-ics-cleaner"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def fold(line):
    # Split at 75 octets without breaking a UTF-8 character.
    out, buf, limit = [], b"", 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(buf) + len(b) > limit:
            out.append(buf)
            buf, limit = b" ", 75
        buf += b
    out.append(buf)
    return b"\r\n".join(out).decode("utf-8")


def escape_text(line):
    name, _, value = line.partition(":")
    if name.split(";")[0] in TEXT_PROPS:
        value = re.sub(r"(?<!\\)([,;])", r"\\\1", value)
    return f"{name}:{value}"


def end_time(event):
    for line in event:
        if line.startswith(("DTEND", "DTSTART")):
            m = re.search(r"(\d{8}T\d{6})Z", line)
            if m:
                return datetime.strptime(m.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return None


def clean_event(event):
    urls = [l for l in event if l.startswith("URL")]
    # Prefer the stream link over the generic site link.
    keep = next((u for u in urls if "esportscalendar.app" not in u), urls[0] if urls else None)
    out = [l for l in event if not l.startswith("URL")]
    if keep:
        out.insert(-1, keep)
    return [escape_text(l) for l in out]


def main():
    lines = unfold(fetch(SOURCE))
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS_BACK)
    header, events, current = [], [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = [line]
        elif current is not None:
            current.append(line)
            if line == "END:VEVENT":
                events.append(current)
                current = None
        elif line != "END:VCALENDAR":
            header.append(line)

    kept = [clean_event(e) for e in events if (end_time(e) or cutoff) >= cutoff]
    header = [l for l in header if not l.startswith(("REFRESH-INTERVAL", "X-PUBLISHED-TTL"))]
    header += ["REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]

    body = [fold(l) for l in header + [l for e in kept for l in e] + ["END:VCALENDAR"]]
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(body) + "\r\n")
    print(f"{len(events)} events in source, {len(kept)} kept -> {OUT}")


if __name__ == "__main__":
    main()
