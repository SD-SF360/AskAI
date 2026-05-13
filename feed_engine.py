import requests
import feedparser
import random
import re

NEWS_API_KEY = "e9483687581d4fb39447352f50c42dbb"

NEWS_URL = "https://newsapi.org/v2/everything"

RSS_SOURCES = [

    "https://news.google.com/rss/search?q=ipl+cricket&hl=en-IN&gl=IN&ceid=IN:en",

    "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",

    "https://www.icc-cricket.com/rss/media-releases"

]

# Only allow cricket related topics
CRICKET_KEYWORDS = [
    "cricket","ipl","bcci","icc","t20","odi","test",
    "virat","rohit","dhoni","kohli","rcb","csk","mi",
    "kkr","rr","srh","dc","gt","pbks"
]


def is_cricket_news(title):

    if not title:
        return False

    t = title.lower()

    for k in CRICKET_KEYWORDS:
        if k in t:
            return True

    return False


def clean_html(text):

    if not text:
        return ""

    clean = re.sub("<.*?>", "", text)
    return clean[:220]


def get_newsapi_cards():

    cards = []

    try:

        params = {
            "q": "IPL OR cricket OR BCCI",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 8,
            "apiKey": NEWS_API_KEY
        }

        res = requests.get(NEWS_URL, params=params, timeout=6)

        data = res.json()

        for article in data.get("articles", []):

            title = article.get("title")

            if not is_cricket_news(title):
                continue

            cards.append({

                "type": "news",

                "title": title,

                "text": article.get("description") or "Latest cricket update",

                "image": article.get("urlToImage"),

                "link": article.get("url")

            })

    except Exception:
        pass

    return cards


def get_rss_cards():

    cards = []

    for url in RSS_SOURCES:

        try:

            feed = feedparser.parse(url)

            for entry in feed.entries[:6]:

                title = entry.get("title")

                if not is_cricket_news(title):
                    continue

                image = None

                if "media_content" in entry:
                    image = entry.media_content[0]["url"]

                if not image and "links" in entry:
                    for l in entry.links:
                        if "image" in str(l.get("type")):
                            image = l.get("href")

                summary = clean_html(entry.get("summary", ""))

                cards.append({

                    "type": "news",

                    "title": title,

                    "text": summary if summary else "Latest cricket update",

                    "image": image,

                    "link": entry.get("link")

                })

        except Exception:
            continue

    return cards


def get_feed():

    cards = []

    # News API
    cards.extend(get_newsapi_cards())

    # RSS feeds
    cards.extend(get_rss_cards())

    # Remove duplicates
    unique = []
    titles = set()

    for c in cards:

        if c["title"] not in titles:

            unique.append(c)
            titles.add(c["title"])

    # Shuffle feed
    random.shuffle(unique)

    final_cards = unique[:12]

    if not final_cards:

        final_cards = [

            {

                "type": "news",

                "title": "IPL Season Updates",

                "text": "Latest cricket insights and match updates",

                "image": "https://upload.wikimedia.org/wikipedia/en/2/2e/Indian_Premier_League_Logo.svg",

                "link": "https://www.iplt20.com"

            }

        ]

    return {"cards": final_cards}