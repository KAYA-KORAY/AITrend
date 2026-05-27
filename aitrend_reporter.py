#!/usr/bin/env python3
"""Daily AI trend reporter.

Collects AI headlines from curated sources (news sites + visionary people signals),
extracts trend themes, and writes a daily Markdown report.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime as dt
import pathlib
import re
from typing import Iterable

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser


NEWS_SOURCES = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google DeepMind Blog": "https://deepmind.google/blog/rss.xml",
    "Anthropic News": "https://www.anthropic.com/news/rss.xml",
    "NVIDIA Blog": "https://blogs.nvidia.com/feed/",
    "MIT Technology Review - AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
}

# Google News RSS queries for "visionary" people (signal for public discourse).
VISIONARY_PEOPLE = {
    "Sam Altman": "https://news.google.com/rss/search?q=Sam+Altman+AI&hl=en-US&gl=US&ceid=US:en",
    "Demis Hassabis": "https://news.google.com/rss/search?q=Demis+Hassabis+AI&hl=en-US&gl=US&ceid=US:en",
    "Jensen Huang": "https://news.google.com/rss/search?q=Jensen+Huang+AI&hl=en-US&gl=US&ceid=US:en",
    "Yann LeCun": "https://news.google.com/rss/search?q=Yann+LeCun+AI&hl=en-US&gl=US&ceid=US:en",
    "Andrew Ng": "https://news.google.com/rss/search?q=Andrew+Ng+AI&hl=en-US&gl=US&ceid=US:en",
}

THEME_KEYWORDS = {
    "AI Agents": ["agent", "autonomous", "workflow", "orchestration", "copilot"],
    "Model Releases": ["model", "release", "launch", "checkpoint", "benchmark", "reasoning"],
    "Enterprise Adoption": ["enterprise", "business", "customer", "deployment", "productivity"],
    "AI Hardware": ["gpu", "chip", "inference", "datacenter", "semiconductor", "nvidia"],
    "Safety & Policy": ["safety", "policy", "regulation", "governance", "compliance", "risk"],
    "Research Breakthroughs": ["research", "paper", "breakthrough", "state-of-the-art", "sota"],
    "Multimodal/Video": ["multimodal", "vision", "image", "video", "audio", "generation"],
}


@dataclasses.dataclass
class Article:
    title: str
    link: str
    source: str
    published: dt.datetime
    summary: str


def _parse_date(value: str | None) -> dt.datetime:
    if not value:
        return dt.datetime.now(dt.timezone.utc)
    try:
        parsed = dt_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return dt.datetime.now(dt.timezone.utc)


def _clean_html(text: str | None) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def fetch_feed(name: str, url: str, limit: int = 10) -> list[Article]:
    parsed = feedparser.parse(url)
    articles: list[Article] = []
    for e in parsed.entries[:limit]:
        articles.append(
            Article(
                title=getattr(e, "title", "(no title)").strip(),
                link=getattr(e, "link", "").strip(),
                source=name,
                published=_parse_date(getattr(e, "published", None) or getattr(e, "updated", None)),
                summary=_clean_html(getattr(e, "summary", "") or getattr(e, "description", "")),
            )
        )
    return articles


def collect_articles(max_per_source: int = 8) -> list[Article]:
    articles: list[Article] = []
    for name, url in NEWS_SOURCES.items():
        articles.extend(fetch_feed(name, url, max_per_source))
    for person, url in VISIONARY_PEOPLE.items():
        articles.extend(fetch_feed(f"People Signal: {person}", url, max_per_source))
    return sorted(articles, key=lambda x: x.published, reverse=True)


def _score_themes(articles: Iterable[Article]) -> dict[str, int]:
    counts = collections.Counter()
    for article in articles:
        text = f"{article.title} {article.summary}".lower()
        for theme, keywords in THEME_KEYWORDS.items():
            if any(k in text for k in keywords):
                counts[theme] += 1
    return dict(counts)


def _top_articles_by_theme(articles: list[Article], theme: str, limit: int = 3) -> list[Article]:
    keys = THEME_KEYWORDS[theme]
    matched = [a for a in articles if any(k in (a.title + " " + a.summary).lower() for k in keys)]
    return matched[:limit]


def build_inference(articles: list[Article]) -> str:
    if not articles:
        return "No data collected today."

    scores = _score_themes(articles)
    top_themes = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:3]
    if not top_themes:
        return "Signals are too weak today; broaden sources or increase fetch limits."

    parts = []
    for idx, (theme, count) in enumerate(top_themes, start=1):
        sample_titles = "; ".join(a.title for a in _top_articles_by_theme(articles, theme, 2))
        parts.append(
            f"{idx}. **{theme}** appears strongest ({count} related headlines). "
            f"Representative signals: {sample_titles or 'n/a'}."
        )

    recent = articles[:10]
    people_share = sum(1 for a in recent if a.source.startswith("People Signal:"))
    parts.append(
        "4. **Discourse mix**: "
        f"{people_share}/10 of the most recent items come from person-centric signals, "
        "suggesting whether narrative is leader-driven vs product/research-driven."
    )

    return "\n".join(parts)


def generate_report(output_dir: str, days_back: int = 1) -> pathlib.Path:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=days_back)

    all_articles = collect_articles()
    fresh = [a for a in all_articles if a.published >= cutoff]

    report_date = now.strftime("%Y-%m-%d")
    out = pathlib.Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_file = out / f"ai_trend_report_{report_date}.md"

    inference = build_inference(fresh)

    lines = [
        f"# Daily AI Trend Report ({report_date}, UTC)",
        "",
        f"Collected items: **{len(fresh)}** (window: last {days_back} day).",
        "",
        "## Inference Summary",
        inference,
        "",
        "## Top Headlines",
    ]

    for a in fresh[:25]:
        lines.append(f"- **{a.title}** ({a.source}, {a.published.strftime('%Y-%m-%d %H:%M UTC')})")
        if a.link:
            lines.append(f"  - {a.link}")

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file


def ping(url: str, timeout: int = 5) -> bool:
    try:
        requests.get(url, timeout=timeout)
        return True
    except Exception:
        return False


def cli() -> None:
    parser = argparse.ArgumentParser(description="Generate AI trend daily report")
    parser.add_argument("--output-dir", default="reports", help="Directory where report is saved")
    parser.add_argument("--days-back", type=int, default=1, help="How many days to include")
    parser.add_argument("--healthcheck", action="store_true", help="Quick network health check")
    args = parser.parse_args()

    if args.healthcheck:
        targets = ["https://openai.com", "https://news.google.com"]
        ok = all(ping(t) for t in targets)
        print("ok" if ok else "degraded")
        return

    report = generate_report(args.output_dir, args.days_back)
    print(f"Report generated: {report}")


if __name__ == "__main__":
    cli()
