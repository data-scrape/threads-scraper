"""
Threads Scraper - Scrape posts, profiles, and replies from Meta's Threads
Extract post text, media, likes, replies, reposts, and profile data.

For production Threads data, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
from typing import List, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class ThreadsPost:
    post_id: str = ""
    text: str = ""
    author: str = ""
    author_name: str = ""
    created_at: str = ""
    likes: str = ""
    replies: str = ""
    reposts: str = ""
    media_urls: str = ""
    url: str = ""

@dataclass
class ThreadsProfile:
    username: str = ""
    name: str = ""
    bio: str = ""
    followers: str = ""
    following: str = ""
    threads_count: str = ""
    verified: bool = False
    profile_image: str = ""

class ThreadsScraper:
    BASE_URL = "https://www.threads.net"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, proxy: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def get_user_posts(self, username: str, limit: int = 50) -> List[ThreadsPost]:
        url = f"{self.BASE_URL}/@{username}"
        posts = []
        try:
            resp = self.session.get(url, timeout=30)
            data = self._extract_json(resp.text)
            if data:
                for item in data:
                    post = self._parse_thread_item(item, username)
                    if post:
                        posts.append(post)
                    if len(posts) >= limit:
                        break
        except Exception as e:
            print(f"Error scraping @{username}: {e}")
        return posts

    def get_profile(self, username: str) -> ThreadsProfile:
        url = f"{self.BASE_URL}/@{username}"
        profile = ThreadsProfile(username=username)
        try:
            resp = self.session.get(url, timeout=30)
            data = self._extract_json(resp.text)
            if data and isinstance(data, dict):
                user_data = data.get("data", {}).get("userData", {})
                profile.name = user_data.get("name", username)
                profile.bio = user_data.get("bio", "")
                profile.followers = str(user_data.get("follower_count", ""))
                profile.following = str(user_data.get("following_count", ""))
                profile.threads_count = str(user_data.get("thread_count", ""))
                profile.verified = user_data.get("verified", False)
                profile.profile_image = user_data.get("profile_pic_url", "")
        except Exception as e:
            print(f"Error getting profile @{username}: {e}")
        return profile

    def _extract_json(self, html: str) -> Optional[dict]:
        match = re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", type="application/json")
        if script:
            try:
                return json.loads(script.string)
            except Exception:
                pass
        return None

    def _parse_thread_item(self, item: dict, username: str) -> Optional[ThreadsPost]:
        try:
            post = ThreadsPost()
            post.post_id = str(item.get("code", item.get("id", "")))
            post.text = item.get("caption", {}).get("text", "") if isinstance(item.get("caption"), dict) else str(item.get("caption", ""))
            post.author = username
            post.created_at = str(item.get("taken_at", ""))
            post.likes = str(item.get("like_count", ""))
            post.replies = str(item.get("text_post_info", {}).get("direct_reply_count", "")) if isinstance(item.get("text_post_info"), dict) else ""
            post.reposts = str(item.get("text_post_info", {}).get("repost_count", "")) if isinstance(item.get("text_post_info"), dict) else ""
            post.url = f"{self.BASE_URL}/@{username}/post/{post.post_id}"
            carousel = item.get("carousel_media", [])
            if carousel:
                urls = []
                for media in carousel:
                    if isinstance(media, dict):
                        img = media.get("image_versions2", {})
                        if isinstance(img, dict):
                            urls.append(img.get("url", ""))
                post.media_urls = ",".join(urls)
            return post if post.text or post.post_id else None
        except Exception:
            return None

    @staticmethod
    def export_json(data, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(d) if hasattr(d, "__dataclass_fields__") else d for d in data], f, indent=2)
        print(f"Exported {len(data)} items to {filepath}")

    @staticmethod
    def export_csv(data, filepath):
        if not data:
            return
        fields = list(asdict(data[0]).keys()) if hasattr(data[0], "__dataclass_fields__") else list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for item in data:
                w.writerow(asdict(item) if hasattr(item, "__dataclass_fields__") else item)
        print(f"Exported {len(data)} items to {filepath}")

def main():
    p = argparse.ArgumentParser(description="Threads Scraper")
    p.add_argument("--user", "-u", help="Threads username (without @)")
    p.add_argument("--profile", action="store_true", help="Get profile info")
    p.add_argument("--limit", "-n", type=int, default=50)
    p.add_argument("--output", "-o", default="threads_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = ThreadsScraper(proxy=args.proxy)
    if not args.user:
        print("Provide --user")
        return
    if args.profile:
        data = [s.get_profile(args.user)]
    else:
        data = s.get_user_posts(args.user, args.limit)
    ext = "json" if args.format == "json" else "csv"
    ThreadsScraper.export_json(data, f"{args.output}.{ext}") if args.format == "json" else ThreadsScraper.export_csv(data, f"{args.output}.{ext}")

if __name__ == "__main__":
    main()
