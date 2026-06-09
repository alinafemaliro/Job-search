"""
biz_scraper.py — Scrapes UK business-for-sale listings under £25,000.
Sources: rightbiz.co.uk, daltonsbusiness.com
"""

import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MAX_PRICE = 25_000

# Food / hospitality keywords — skip unless price ≤ £5,000
FOOD_KEYWORDS = [
    "restaurant", "cafe", "coffee shop", "takeaway", "food outlet",
    "bistro", "brasserie", " pub ", "pub&", "bar &", "pizza", "kebab",
    "fish and chip", "sandwich shop", "tea room", "catering company",
    "fish & chip", "burger shop", "chicken shop", "noodle bar",
    "indian restaurant", "chinese restaurant", "thai restaurant",
]


def is_food_business(title: str, description: str = "") -> bool:
    combined = (title + " " + description).lower()
    return any(kw in combined for kw in FOOD_KEYWORDS)


def _parse_price(text: str) -> int:
    """Return numeric price from text like '£12,500'. Returns 0 if not found."""
    m = re.search(r'£\s*([\d,]+)', text)
    return int(m.group(1).replace(",", "")) if m else 0


def _price_str(num: int) -> str:
    return f"£{num:,}" if num else "POA"


# ─── rightbiz.co.uk ──────────────────────────────────────────────────────────
# Card selector: li.listing-no-slider
# Title:         a.link-title
# Link:          a[href*='/buy_business/'] → prepend base URL
# Price:         .content-body-item-footer-price  (contains £X,XXX)
# Location:      .location-item
# Turnover:      .turnover (first match)

def scrape_rightbiz(max_price: int = MAX_PRICE, pages: int = 10) -> list[dict]:
    results = []
    seen: set[str] = set()

    for page in range(1, pages + 1):
        # Scrape all listings, filter client-side (sort param breaks pagination)
        url = (
            f"https://www.rightbiz.co.uk/businesses-for-sale-in-uk.html"
            f"?page={page}"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("li.listing-no-slider")

            if not cards:
                break

            for card in cards:
                title_el = card.select_one("a.link-title")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                href  = title_el.get("href", "")
                if href and not href.startswith("http"):
                    href = "https://www.rightbiz.co.uk" + href
                if not href or href in seen:
                    continue

                price_el  = card.select_one(".content-body-item-footer-price")
                price     = _parse_price(price_el.get_text() if price_el else "")
                price_str = _price_str(price)

                loc_el   = card.select_one(".location-item")
                location = loc_el.get_text(strip=True) if loc_el else ""

                # First .turnover element has "Turnover: £X,XXX ..."
                tv_el    = card.select_one(".turnover")
                turnover = ""
                if tv_el:
                    tv_text = tv_el.get_text(" ", strip=True)
                    tv_m    = re.search(r'Turnover[:\s]+£?([\d,]+)', tv_text, re.I)
                    if tv_m:
                        turnover = f"£{tv_m.group(1)}"

                # Profit line
                profit = ""
                profit_els = card.select(".turnover")
                for pe in profit_els:
                    pt = pe.get_text(" ", strip=True)
                    if "Profit:" in pt or "profit" in pt.lower():
                        pm = re.search(r'Profit[:\s]+£?([\d,]+)', pt, re.I)
                        if pm:
                            profit = f"£{pm.group(1)}"
                        break

                description = card.get_text(" ", strip=True)[:400]

                results.append({
                    "title":       title,
                    "price":       price,
                    "price_str":   price_str,
                    "location":    location,
                    "turnover":    turnover,
                    "profit":      profit,
                    "description": description,
                    "link":        href,
                    "source":      "rightbiz.co.uk",
                })
                seen.add(href)

            time.sleep(1.5)

        except Exception as e:
            print(f"     ⚠  rightbiz page {page}: {e}")

    return results


# ─── daltonsbusiness.com ─────────────────────────────────────────────────────
# Card selector: .item-wrap  (parent.parent of .item-header)
# Title:         h2.item-title / h3.item-title
# Link:          a[href*='/listing/']
# Price:         .item-price-text  (text like "Leasehold: £49,950")
# Location:      text after title (contains city, county, England pattern)
# Turnover:      parse from full card text

def scrape_daltons(max_price: int = MAX_PRICE, pages: int = 10) -> list[dict]:
    results = []
    seen: set[str] = set()

    for page in range(1, pages + 1):
        url = (
            f"https://www.daltonsbusiness.com/listing-businesses-for-sale/"
            f"page/{page}/"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break

            soup  = BeautifulSoup(resp.text, "html.parser")
            # Each card: parent.parent of .item-header
            item_headers = soup.select(".item-header")
            if not item_headers:
                break

            for ih in item_headers:
                card = ih.parent.parent   # .item-wrap div

                title_el = card.select_one("h2.item-title, h3.item-title, .item-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                # Trim trailing location that bleeds into title on some cards
                title = title.split("\n")[0].strip()

                link_el = card.find("a", href=lambda h: h and "/listing/" in str(h))
                href    = link_el.get("href", "") if link_el else ""
                if not href or href in seen:
                    continue

                price_el  = card.select_one(".item-price-text, .item-price")
                price     = _parse_price(price_el.get_text() if price_el else "")
                price_str = _price_str(price)

                # Location: look for county/city pattern in card text
                text     = card.get_text(" ", strip=True)
                loc_m    = re.search(
                    r'\b(London|Manchester|Birmingham|Bristol|Edinburgh|Glasgow|Leeds|'
                    r'Sheffield|Liverpool|Newcastle|Nottingham|Leicester|Cardiff|Belfast|'
                    r'Oxford|Cambridge|Brighton|Reading|Coventry|Rutland|'
                    r'[\w\s]+ , [\w\s]+ , England|[\w\s]+ , [\w\s]+ , Scotland|'
                    r'[\w\s]+ , [\w\s]+ , Wales)',
                    text
                )
                location = loc_m.group(0).strip() if loc_m else ""

                tv_m     = re.search(
                    r'(?:Annual\s+Revenue|Turnover|Revenue)[^£]*£?([\d,]+)',
                    text, re.I
                )
                turnover = f"£{tv_m.group(1)}" if tv_m else ""

                profit_m = re.search(r'Profit[^£]*£?([\d,]+)', text, re.I)
                profit   = f"£{profit_m.group(1)}" if profit_m else ""

                results.append({
                    "title":       title,
                    "price":       price,
                    "price_str":   price_str,
                    "location":    location,
                    "turnover":    turnover,
                    "profit":      profit,
                    "description": text[:400],
                    "link":        href,
                    "source":      "daltonsbusiness.com",
                })
                seen.add(href)

            time.sleep(1.5)

        except Exception as e:
            print(f"     ⚠  daltons page {page}: {e}")

    return results


# ─── Main entry point ────────────────────────────────────────────────────────

def scrape_all(max_price: int = MAX_PRICE) -> list[dict]:
    """Scrape all sources, deduplicate, filter by price and food type."""
    all_listings: list[dict] = []
    seen: set[str] = set()

    sources = [
        ("rightbiz.co.uk",     lambda: scrape_rightbiz(max_price)),
        ("daltonsbusiness.com", lambda: scrape_daltons(max_price)),
    ]

    for name, fn in sources:
        print(f"     🔍 {name} …")
        try:
            batch = fn()
            added = 0
            for l in batch:
                if l["link"] not in seen:
                    all_listings.append(l)
                    seen.add(l["link"])
                    added += 1
            print(f"        → {added} listings")
        except Exception as e:
            print(f"        ⚠  {name} failed: {e}")

    # Split into priced (≤ max_price) and POA (price unknown — may be negotiable)
    priced_listings = [l for l in all_listings if 0 < l["price"] <= max_price]
    poa_listings    = [l for l in all_listings if l["price"] == 0]

    def keep(l: dict) -> bool:
        """Return True unless it's a food business above the bargain threshold."""
        if is_food_business(l["title"], l.get("description", "")):
            return 0 < l["price"] <= 5_000  # keep only very cheap food businesses
        return True

    priced_ok = [l for l in priced_listings if keep(l)]
    poa_ok    = [l for l in poa_listings    if keep(l)]

    # Mark POA listings so Claude knows to flag them
    for l in poa_ok:
        l["price_str"] = "POA (price on application — negotiate)"

    # Priced cheapest first, then POA (capped at 30 to avoid overloading Claude)
    priced_ok.sort(key=lambda x: x["price"])
    filtered = priced_ok + poa_ok[:30]

    print(f"     → {len(priced_ok)} priced under £{max_price:,}  +  {len(poa_ok[:30])} POA listings")
    return filtered


def format_for_claude(listings: list[dict], limit: int = 60) -> str:
    """Format listings as plain text for the Claude analysis prompt."""
    if not listings:
        return "No listings found."

    subset = listings[:limit]
    lines  = [f"UK BUSINESSES FOR SALE — {len(subset)} LISTINGS UNDER £{MAX_PRICE:,}\n"]

    for i, l in enumerate(subset, 1):
        lines.append(
            f"{i}. {l['title']}\n"
            f"   Price:    {l['price_str']}\n"
            f"   Location: {l['location'] or 'UK'}\n"
            f"   Turnover: {l['turnover'] or 'not stated'}\n"
            f"   Profit:   {l['profit'] or 'not stated'}\n"
            f"   Source:   {l['source']}\n"
            f"   Link:     {l['link']}\n"
            f"   Details:  {l['description'][:250].strip()}\n"
        )

    return "\n".join(lines)


# ─── Quick test when run directly ────────────────────────────────────────────

if __name__ == "__main__":
    listings = scrape_all()
    print("\n" + format_for_claude(listings, limit=5))
