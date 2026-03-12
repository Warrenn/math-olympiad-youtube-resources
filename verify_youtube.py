#!/usr/bin/env python3
"""
Verify YouTube search strings by searching each on youtube.com
and recording the first video result.
"""

import csv
import re
import time
import urllib.parse
from playwright.sync_api import sync_playwright

SEARCH_STRINGS = [
    "Art of Problem Solving cryptarithmetic alphametic introduction",
    "Art of Problem Solving custom operations defined",
    "Art of Problem Solving modular arithmetic introduction",
    "Art of Problem Solving pigeonhole principle",
    "Art of Problem Solving telescoping series",
    "Corbett Maths area compound shapes",
    "Corbett Maths area on a grid",
    "Corbett Maths dividing decimals",
    "Corbett Maths divisibility rules",
    "Corbett Maths number pyramids",
    "Corbett Maths ratio proportion",
    "Corbett Maths symmetry",
    "Eddie Woo area irregular shapes grid surround subtract",
    "Eddie Woo geometric sequences introduction",
    "Eddie Woo handshake problem",
    "Eddie Woo last digit patterns powers cycles",
    "Eddie Woo maximum regions lines dividing plane",
    "Eddie Woo painted cube problem faces",
    "Eddie Woo simultaneous equations introduction",
    "Eddie Woo solving simple equations backtracking",
    "Eddie Woo sum of cubes formula proof",
    "Eddie Woo triangular numbers",
    "Khan Academy Fibonacci sequence",
    "Khan Academy Sieve of Eratosthenes",
    "Khan Academy age word problems algebra",
    "Khan Academy area of composite figures",
    "Khan Academy coin word problems algebra",
    "Khan Academy distributive property",
    "Khan Academy dividing decimals",
    "Khan Academy divisibility tests 2 3 4 5 6 9 10",
    "Khan Academy finding area on a grid",
    "Khan Academy intro to geometric sequences",
    "Khan Academy intro to reflective symmetry lines of symmetry",
    "Khan Academy introduction to fractions",
    "Khan Academy introduction to rates unit rates",
    "Khan Academy number line movement addition subtraction",
    "Khan Academy order of operations introduction",
    "Khan Academy rates work problems two pipes filling",
    "Khan Academy solving proportions",
    "Khan Academy solving system of 3 equations substitution",
    "Khan Academy sum first n integers Gauss formula",
    "Khan Academy triangular numbers patterns",
    "Khan Academy why we do same thing both sides simple equation",
    "Mashup Math distributive property explained",
    "Mashup Math solving one-step equations",
    "Math Antics Adding Subtracting Fractions",
    "Math Antics Area composite shapes",
    "Math Antics Basic Probability",
    "Math Antics Divisibility Rules",
    "Math Antics Exponents Square Roots",
    "Math Antics Factors and Multiples",
    "Math Antics Finding a Percent of a Number",
    "Math Antics Fractions Are Parts",
    "Math Antics Least Common Multiple",
    "Math Antics Long Division",
    "Math Antics Perimeter",
    "Math Antics Proportions",
    "Math Antics Ratios and Rates",
    "Math Antics Solving 2-Step Equations",
    "Math Antics Symmetry",
    "Math Antics What Are Percentages",
    "Math Antics What Is Algebra",
    "Math Antics Working With Parts",
    "Math Antics arithmetic sequences",
    "Math Antics integers number line positive negative",
    "Math with Mr J age word problems",
    "Math with Mr J calendar math days dates",
    "Math with Mr J distributive property 3rd 4th 5th grade",
    "Math with Mr J divisibility rules",
    "Math with Mr J money word problems",
    "Math with Mr J rounding decimals",
    "MindYourDecisions SEND MORE MONEY cryptarithmetic",
    "NUMBEROCK LCM song least common multiple",
    "NUMBEROCK divisibility rules song",
    "NUMBEROCK fractions song for kids",
    "NUMBEROCK ratios song for kids",
    "NUMBEROCK symmetry song for kids",
    "Numberphile Fibonacci sequence nature",
    "Numberphile Gauss trick 1 to 100 sum",
    "Numberphile painted cube",
    "Numberphile triangular numbers",
    "Organic Chemistry Tutor age word problems",
    "Organic Chemistry Tutor solving system of equations 3 variables",
    "Organic Chemistry Tutor work rate problems pipes",
    "Silly School Songs Order of Operations PEMDAS",
    "Vi Hart doodling math spirals Fibonacci",
]

OUTPUT_CSV = "/Users/warrennenslin/workbench/experiment/math_olympiad/verified_youtube_links.csv"
BATCH_SIZE = 10


def extract_expected_channel(search_string: str) -> str:
    """Extract the expected channel name from the search string."""
    # Known channel name prefixes (order matters - longer first)
    channels = [
        "Art of Problem Solving",
        "Organic Chemistry Tutor",
        "Silly School Songs",
        "Math with Mr J",
        "Corbett Maths",
        "MindYourDecisions",
        "Khan Academy",
        "Mashup Math",
        "Math Antics",
        "Eddie Woo",
        "NUMBEROCK",
        "Numberphile",
        "Vi Hart",
    ]
    for ch in channels:
        if search_string.startswith(ch):
            return ch
    return ""


def get_first_video_result(page) -> dict:
    """
    Extract the first video result from a YouTube search results page.
    Returns dict with title, channel, url or None values.
    """
    # Wait for video results to load
    try:
        page.wait_for_selector("ytd-video-renderer", timeout=10000)
    except Exception:
        return {"title": "", "channel": "", "url": "", "video_id": ""}

    # Use JS to extract the first video renderer's data
    result = page.evaluate("""
    () => {
        const videos = document.querySelectorAll('ytd-video-renderer');
        for (const video of videos) {
            // Skip ads (they have a different structure or ad badge)
            const adBadge = video.querySelector('ytd-ad-slot-renderer, [class*="ad-badge"]');
            if (adBadge) continue;

            const titleEl = video.querySelector('#video-title');
            const channelEl = video.querySelector('#channel-name #text-container yt-formatted-string a')
                           || video.querySelector('#channel-name yt-formatted-string a')
                           || video.querySelector('ytd-channel-name #text-container yt-formatted-string a')
                           || video.querySelector('ytd-channel-name yt-formatted-string a');
            const linkEl = video.querySelector('a#video-title');

            const title = titleEl ? titleEl.textContent.trim() : '';
            const channel = channelEl ? channelEl.textContent.trim() : '';
            const href = linkEl ? linkEl.getAttribute('href') : '';

            if (title && href) {
                // Extract video ID from href
                const match = href.match(/\\/watch\\?v=([^&]+)/);
                const videoId = match ? match[1] : '';
                return {
                    title: title,
                    channel: channel,
                    url: videoId ? 'https://www.youtube.com/watch?v=' + videoId : '',
                    video_id: videoId
                };
            }
        }
        return {title: '', channel: '', url: '', video_id: ''};
    }
    """)
    return result


def channel_matches(expected: str, actual: str) -> bool:
    """Check if the actual channel name is a reasonable match for expected."""
    if not expected or not actual:
        return False
    exp = expected.lower().strip()
    act = actual.lower().strip()

    # Direct containment
    if exp in act or act in exp:
        return True

    # Known aliases
    aliases = {
        "art of problem solving": ["aops", "art of problem solving", "artofproblemsolving"],
        "organic chemistry tutor": ["the organic chemistry tutor"],
        "corbett maths": ["corbettmaths", "corbett maths"],
        "math antics": ["mathantics", "math antics"],
        "khan academy": ["khan academy"],
        "eddie woo": ["eddie woo", "wootube"],
        "numberphile": ["numberphile"],
        "numberock": ["numberock"],
        "mashup math": ["mashup math", "mashupmathc"],
        "math with mr j": ["math with mr. j", "math with mr j"],
        "mindyourdecisions": ["mindyourdecisions", "mind your decisions", "presh talwalkar"],
        "vi hart": ["vi hart", "vihart"],
        "silly school songs": ["silly school", "silly school songs"],
    }
    for key, vals in aliases.items():
        if exp == key:
            return any(v in act for v in vals)
    return False


def escape_csv_field(field: str) -> str:
    """Escape a field for CSV output."""
    # csv module handles this, but ensure we clean up newlines
    return field.replace("\n", " ").replace("\r", "")


def main():
    # Write CSV header
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["search_string", "video_title", "channel_name", "url", "status"])

    results = []
    total = len(SEARCH_STRINGS)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        page = context.new_page()

        # First visit YouTube to accept any consent
        page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        # Try to dismiss consent dialog if present
        try:
            consent_btn = page.query_selector('button[aria-label*="Accept"], button:has-text("Accept all"), tp-yt-paper-button:has-text("Accept all")')
            if consent_btn:
                consent_btn.click()
                time.sleep(1)
        except Exception:
            pass

        for i, search_string in enumerate(SEARCH_STRINGS):
            idx = i + 1
            print(f"[{idx}/{total}] Searching: {search_string}")

            expected_channel = extract_expected_channel(search_string)
            encoded_query = urllib.parse.quote_plus(search_string)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)  # Let results render

                video = get_first_video_result(page)

                if video["title"] and video["url"]:
                    # Determine status
                    if channel_matches(expected_channel, video["channel"]):
                        status = "FOUND"
                    else:
                        status = "NOT_FOUND"
                        print(f"  -> Channel mismatch: expected '{expected_channel}', got '{video['channel']}'")

                    row = {
                        "search_string": search_string,
                        "video_title": escape_csv_field(video["title"]),
                        "channel_name": escape_csv_field(video["channel"]),
                        "url": video["url"],
                        "status": status,
                    }
                else:
                    row = {
                        "search_string": search_string,
                        "video_title": "",
                        "channel_name": "",
                        "url": "",
                        "status": "NOT_FOUND",
                    }
                    print(f"  -> No video result found")

            except Exception as e:
                print(f"  -> Error: {e}")
                row = {
                    "search_string": search_string,
                    "video_title": "",
                    "channel_name": "",
                    "url": "",
                    "status": "NOT_FOUND",
                }

            results.append(row)
            print(f"  -> {row['status']}: {row['video_title'][:60]}... | {row['channel_name']} | {row['url']}")

            # Write batch every BATCH_SIZE
            if len(results) % BATCH_SIZE == 0 or idx == total:
                batch_start = (len(results) - 1) // BATCH_SIZE * BATCH_SIZE
                batch = results[batch_start:]
                with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for r in batch:
                        writer.writerow([r["search_string"], r["video_title"], r["channel_name"], r["url"], r["status"]])
                print(f"  [Batch written to CSV - {len(results)}/{total} complete]")

            # Small delay to avoid rate limiting
            if idx < total:
                time.sleep(1.5)

        browser.close()

    # Print summary
    found = sum(1 for r in results if r["status"] == "FOUND")
    not_found = sum(1 for r in results if r["status"] == "NOT_FOUND")
    broken = sum(1 for r in results if r["status"] == "BROKEN")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total searched: {total}")
    print(f"Found: {found}")
    print(f"Not found: {not_found}")
    print(f"Broken: {broken}")
    print(f"CSV file: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
