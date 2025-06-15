import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import json
import os
import time

# 🌍 RSS Feeds
FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
}

# 🧹 Extract clean <p> tags with NO attributes
def extract_article_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [
            p.get_text().strip()
            for p in soup.find_all("p")
            if not p.attrs  # ✅ No attributes at all
        ]
        full_text = "\n".join(p for p in paragraphs if p)
        return full_text

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Network error for {url}: {e}")
    except Exception as e:
        print(f"⚠️ Error extracting content from {url}: {e}")
    return ""

# 🧠 Load previously stored links to prevent duplicates
def load_existing_links(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                return {article["link"] for article in data}
            except json.JSONDecodeError:
                return set()
    return set()

# 💾 Save new articles to file
def save_articles(file_path, new_articles):
    if not new_articles:
        return
    existing_articles = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            try:
                existing_articles = json.load(file)
            except json.JSONDecodeError:
                pass

    existing_articles.extend(new_articles)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(existing_articles, file, indent=2, ensure_ascii=False)

# 🔁 Main fetch loop
def fetch_and_store_news(file_path):
    stored_links = load_existing_links(file_path)
    new_articles = []

    for source, url in tqdm(FEEDS.items(), desc="🔎 Parsing RSS Feeds"):
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo:
                print(f"⚠️ Malformed feed from {source}: {parsed.bozo_exception}")
                continue

            for entry in parsed.entries:
                link = entry.get("link")
                if not link or link in stored_links:
                    continue

                article_text = extract_article_content(link)

                news = {
                    "source": source,
                    "title": entry.get("title", ""),
                    "published": entry.get("published", ""),
                    "link": link,
                    "description": entry.get("summary", ""),
                    "content": article_text,
                    "fetched_at": datetime.utcnow().isoformat() + "Z"
                }

                new_articles.append(news)
                stored_links.add(link)

        except Exception as feed_err:
            print(f"❌ Error parsing feed from {source}: {feed_err}")

    save_articles(file_path, new_articles)
    print(f"✅ {len(new_articles)} new articles saved at {datetime.now().strftime('%H:%M:%S')}")

# 🚀 Runner
if __name__ == "__main__":
    FILE_PATH = "news_articles.json"
    print("🔄 Starting continuous news collection (every 10 seconds)...")
    while True:
        fetch_and_store_news(FILE_PATH)
        time.sleep(10)
