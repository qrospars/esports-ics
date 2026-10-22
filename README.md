# esports-ics

Outlook-compatible mirror of an [esportscalendar.app](https://esportscalendar.app) feed.

The source feed puts two `URL` properties on many events and does not fold long lines,
which Outlook rejects. A GitHub Action fetches it daily, fixes both, drops events older
than a week, and publishes the result with GitHub Pages.

Subscribe in Outlook (Add calendar > Subscribe from web):

https://qrospars.github.io/esports-ics/calendar.ics

To mirror a different feed, change `SOURCE_URL` in `clean_ics.py`.
