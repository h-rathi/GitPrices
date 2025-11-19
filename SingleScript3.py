#!/usr/bin/env python3
"""
compare_prices_append.py

Modified to take Samsung and Amazon URLs from lists declared in the file (no CLI args).
Everything else kept the same: Samsung pages have no mouse movements/clicks/scrolls,
Amazon keeps human-like movements. Results are appended to prices_comparison.xlsx.

Requirements: playwright, beautifulsoup4, pandas, openpyxl
Install: pip install playwright beautifulsoup4 pandas openpyxl
and: playwright install

Run:
python compare_prices_append.py
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError


# ---------------------- Configuration (use lists here) ----------------------

# Put the Samsung URLs you want scraped here (list variable)
SAMSUNG_URLS = [
    "https://www.samsung.com/us/smartphones/galaxy-z-fold7/buy/galaxy-z-fold7-512gb-unlocked-sku-sm-f966udbexaa/",
    "https://www.samsung.com/us/smartphones/galaxy-s25-ultra/buy/galaxy-s25-ultra-256gb-unlocked-sku-sm-s938uzkaxaa/",
    "https://www.samsung.com/us/smartphones/galaxy-z-flip7/buy/galaxy-z-flip7-256gb-unlocked-sku-sm-f766ulgaxaa/",
    "https://www.samsung.com/us/smartphones/galaxy-s25-ultra/buy/galaxy-s25-edge-256gb-unlocked-sku-sm-s937uzsaxaa/"

    # add more samsung urls as needed
]

# Put the Amazon URLs you want scraped here (list variable)
AMAZON_URLS = [
    "https://www.amazon.com/Samsung-Smartphone-Unlocked-Manufacturer-Warranty/dp/B0F7JRKGH1/ref=sr_1_3?crid=2IIQ350CABWC7&keywords=galaxy%2Bz%2Bfold%2B7",
    "https://www.amazon.com/Smartphone-Unlocked-Processor-Manufacturer-Warranty/dp/B0DP3G4GVQ/ref=sr_1_1_sspa?crid=10TW4LFRAIOBO&dib=eyJ2IjoiMSJ9.uqQhueQzsbHe8zENbFmj7bUk0vIwEpi-0APakuwi3hHMu2vGmVltlmCoeqExLjwwHe1NY_y-eiRAZze4TELqwF9A5Z3q2WMC2EPG0p4nD5aGis4NWae_K-CRmvy0IwyOTABmJrdT_nBArRg_3HUXEeD8RiVcw9SrqiFQb-CKPztbZuf4z8k2ncgbVn8qKqGMwy7rSG9Br5vXcD_F-IobKCrdhThEoUQ0RDqrmYpPZPI.EY_aE-DTUSHzDMHcvx2u1pDmmaEgKrcYAQ31_D796hk&dib_tag=se&keywords=s25%2Bultra&qid=1763542293&sprefix=s25%2Caps%2C425&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1",
    "https://www.amazon.com/Samsung-Smartphone-Unlocked-Manufacturer-Warranty/dp/B0F7K3FRNP/ref=sr_1_1_sspa?crid=ZFFPIZBZ98GJ&dib=eyJ2IjoiMSJ9.UCywTCyyKG4bvq7perU6WJwDnwocjQBoU_CBTt0iLEilFUxs7eGFZYXZpU_ioObwnwWuyf6rjjxKURGHvrFykwP0YDyTNEHIJ6iMdK6L--UC4Xf9otHkBAGnuMrKXhDVPrKXBcX3EASPQMHPmIxeZyAUQDkEAC7kjvwYOc851BfCkl7yfIKNjFbb5-rq1n_ZNuEDFncqGGsmuRczfLMtzrq4HfNQyihnc2SfvotrbB8.gsaBvxdWlghc5_yM6ADh4JkaCZsCGwTYiwGF4rklYiw&dib_tag=se&keywords=galaxy%2Bz%2Bflip%2B7&qid=1763542634&sprefix=galaxy%2Bz%2Bflip7%2B%2Caps%2C427&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1",
    "https://www.amazon.com/SAMSUNG-Smartphone-Processor-ProScaler-Manufacturer/dp/B0DYVMVZSY/ref=sr_1_1_sspa?crid=18N7Z6JOQP2BV&dib=eyJ2IjoiMSJ9.nzLYfcsJ7KheFLAc8b9qkf36-GLK18wvNZAtoNJSu1Zuk0LTOxwvIqqD7blO0fqQDvGW1a_cFlDg5Nh6UJs25ksORtqvnynWCvMs3mnXvO49ZOy1Lc0OCa8xgu_zDwki3AucEZejB1tiHQzt8KYuAH3-YcGmTnO7s-Wn_1i_JPAcSstuLawUyqxRadquHocmToV-_PuNbtIeLyuTmsuGn88G4Hs_fJCfV7dzS_zI9l8.tjLmW8sTlnkCiJoCZPOQgL3qCTpiGvJ6gp9QKjm7R24&dib_tag=se&keywords=galaxy%2Bs25%2Bedge&qid=1763542733&sprefix=galaxy%2Bs25%2Bed%2Caps%2C351&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1"

    # add more amazon urls as needed
]

# Directory to save HTML files and where cookies files will be written
OUTPUT_DIR = "scraped_html"


# ---------------------- Utilities ----------------------

def safe_html_name(prefix, index, url):
    """Generate a safe HTML filename for a scraped URL using index."""
    parsed = urlparse(url)
    host = parsed.netloc.replace('.', '_') if parsed.netloc else 'site'
    return f"{prefix}_{host}_{index}.html"


def price_text_to_float(price_text):
    """Convert a price string like '$1,299.00' to float 1299.0. Return None if price_text is None."""
    if not price_text:
        return None
    text = re.sub(r"[^\d\.]", "", price_text)
    try:
        return float(text)
    except Exception:
        return None


# ---------------------- Samsung (no mouse movements) ----------------------

async def wait_network_idle(page, timeout=15000):
    """Wait until network becomes idle (0 active requests)."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except TimeoutError:
        print("⚠️ networkidle timeout — continuing anyway")


async def save_samsung_html_list(urls,
                                 output_dir='.',
                                 cookies_file='samsung_cookies.json'):
    """Loop over samsung urls, save HTML and extract price using the exact original logic (no mouse moves)."""
    results = []
    # Ensure output_dir exists
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # Use a single context per run, loading cookies if present
        if os.path.exists(cookies_file):
            context = await browser.new_context(storage_state=cookies_file)
        else:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1600, "height": 900},
            )

        page = await context.new_page()

        for i, url in enumerate(urls, start=1):
            output_file = os.path.join(output_dir, safe_html_name('samsung', i, url))
            print(f"Samsung: Navigating to {url} ...")
            try:
                await page.goto(url, wait_until="domcontentloaded")
            except Exception as e:
                print("❌ Failed to goto Samsung URL:", e)
                # save whatever content if available
                try:
                    html = await page.content()
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                except Exception:
                    pass
                results.append({
                    'site': 'Samsung',
                    'url': url,
                    'price_text': None,
                    'price_value': None,
                    'html_file': output_file,
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                })
                continue

            # Wait full load
            print("Samsung: Waiting for network to be idle...")
            await wait_network_idle(page, timeout=20000)

            # Wait for device selector
            print("Samsung: Waiting for #device_info box...")
            try:
                await page.wait_for_selector("#device_info", timeout=20000)
            except TimeoutError:
                print("❌ #device_info did NOT load — Samsung blocked or loaded too slowly.")
                html = await page.content()
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(html)
                results.append({
                    'site': 'Samsung',
                    'url': url,
                    'price_text': None,
                    'price_value': None,
                    'html_file': output_file,
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                })
                continue

            # Extra wait for prices inside #device_info
            try:
                await page.wait_for_selector("#device_info span", timeout=15000)
            except TimeoutError:
                pass

            # Save HTML
            html = await page.content()
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"✅ Samsung HTML saved to {output_file}")

            # Parse saved HTML
            price_text = extract_samsung_price(output_file)
            price_value = price_text_to_float(price_text)

            results.append({
                'site': 'Samsung',
                'url': url,
                'price_text': price_text,
                'price_value': price_value,
                'html_file': output_file,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            })

        # Save cookies/session
        try:
            storage = await context.storage_state()
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(storage, f, indent=2)
        except Exception:
            pass

        await browser.close()

    return results


def extract_samsung_price(filename):
    """Extract 512GB model price from saved HTML using BeautifulSoup (exact logic preserved)."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
    except Exception as e:
        print("❌ Failed to open Samsung HTML:", e)
        return None

    container = soup.find(id="device_info")
    if not container:
        print("❌ device_info not found in HTML")
        return None

    radios = container.find_all(attrs={"role": "radio"})
    target = None

    # Prefer aria-checked=true
    for r in radios:
        if r.get("aria-checked") == "true":
            target = r
            break

    # Otherwise find 512GB
    if target is None:
        for r in radios:
            if "512" in r.get_text():
                target = r
                break

    if not target:
        print("❌ Could not find 512GB radio")
        return None

    # Extract price
    text = target.get_text("\n", strip=True)
    prices = re.findall(r"\$\s*[\d,]+\.\d{2}", text)

    # Choose price that is NOT a "was:" value
    selected = None
    for line in text.split("\n"):
        if "$" in line and "was" not in line.lower():
            m = re.search(r"\$\s*[\d,]+\.\d{2}", line)
            if m:
                selected = m.group(0)
                break

    print("Samsung 🔎 Extracted Price:", selected or (prices[-1] if prices else None))
    return selected or (prices[-1] if prices else None)


# ---------------------- Amazon (keeps movements) ----------------------

async def human_delay(min_sec=0.5, max_sec=2.5):
    """Wait for a random time between min_sec and max_sec seconds."""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def save_amazon_html_list(urls,
                                 output_dir='.',
                                 cookies_file='amazon_cookies.json'):
    """Loop over amazon urls, save HTML and extract price using the exact original logic (with movements)."""
    results = []
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)

        if os.path.exists(cookies_file):
            print("🍪 Loading existing cookies/session...")
            context = await browser.new_context(storage_state=cookies_file)
        else:
            print("🆕 No cookies found, creating a new session...")
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
            )

        page = await context.new_page()

        for i, url in enumerate(urls, start=1):
            output_file = os.path.join(output_dir, safe_html_name('amazon', i, url))
            print(f"Amazon: Navigating to {url} ...")
            try:
                await page.goto(url, wait_until="load")
            except Exception as e:
                print("❌ Failed to goto Amazon URL:", e)
                try:
                    html = await page.content()
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                except Exception:
                    pass
                results.append({
                    'site': 'Amazon',
                    'url': url,
                    'price_text': None,
                    'price_value': None,
                    'html_file': output_file,
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                })
                continue

            # Wait randomly for page content to settle
            await human_delay(3, 6)

            # 🖱️ Simulate random human-like mouse movement (kept exactly as original)
            for _ in range(3):
                x = random.randint(200, 800)
                y = random.randint(200, 600)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                await human_delay(0.3, 1.5)

            # 🖱️ Random scrolling (kept)
            for _ in range(2):
                scroll_y = random.randint(400, 1000)
                await page.mouse.wheel(0, scroll_y)
                await human_delay(1, 3)

            # Extract HTML
            html_content = await page.content()
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ Amazon HTML saved to {output_file}")

            # Parse saved HTML
            price_text = extract_amazon_price(output_file)
            price_value = price_text_to_float(price_text)

            results.append({
                'site': 'Amazon',
                'url': url,
                'price_text': price_text,
                'price_value': price_value,
                'html_file': output_file,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            })

        # Save cookies/session state
        try:
            storage_state = await context.storage_state()
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(storage_state, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

        await browser.close()

    return results


def extract_amazon_price(html_file_path="amazon.html"):
    """Parse amazon.html using the exact provided logic to find price spans."""
    try:
        with open(html_file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except Exception as e:
        print("❌ Failed to open Amazon HTML:", e)
        return None

    soup = BeautifulSoup(html_content, "lxml")

    price = None
    price_whole = soup.find("span", {"class": "a-price-whole"})
    price_fraction = soup.find("span", {"class": "a-price-fraction"})
    price_symbol = soup.find("span", {"class": "a-price-symbol"})

    if price_whole and price_fraction:
        price = (price_symbol.get_text().strip() if price_symbol else "$") + \
                price_whole.get_text().strip() + "." + price_fraction.get_text().strip()

    if price:
        print("Amazon 🔎 Extracted Price:", price)
    else:
        print("Amazon: Price not found in the HTML file.")

    return price


# ---------------------- Combine, compare, and append to Excel ----------------------

def append_to_excel(rows, out_file='prices_comparison.xlsx'):
    """Append rows (list of dicts) to the Excel file. If not exists, create new.
    We read the existing file and concat to avoid accidental header/format issues.
    """
    new_df = pd.DataFrame(rows)

    if os.path.exists(out_file):
        try:
            existing = pd.read_excel(out_file)
            combined = pd.concat([existing, new_df], ignore_index=True)
        except Exception as e:
            print("⚠️ Could not read existing Excel file, will overwrite. Error:", e)
            combined = new_df
    else:
        combined = new_df

    combined.to_excel(out_file, index=False)
    print(f"✅ Saved/updated comparison to {out_file}")


async def main(samsung_urls, amazon_urls, output_dir='.'):
    all_rows = []

    # Run Samsung list
    if samsung_urls:
        s_results = await save_samsung_html_list(samsung_urls, output_dir=output_dir)
        all_rows.extend(s_results)

    # Run Amazon list
    if amazon_urls:
        a_results = await save_amazon_html_list(amazon_urls, output_dir=output_dir)
        all_rows.extend(a_results)

    # Add comparison summary per pair if both sites have values for same product URL?
    # For simplicity, provide a global comparison label in each row (keeps original behavior but per-run comparison)
    # Compute numeric values for comparison
    values = [r['price_value'] for r in all_rows if r.get('price_value') is not None]

    if len(values) < 2:
        comparison = 'incomplete (one or both prices missing)'
    else:
        # find min site
        # This is a simple summary across all scraped rows this run
        min_val = min(values)
        sites_with_min = [r['site'] for r in all_rows if r.get('price_value') == min_val]
        comparison = f"Cheapest this run: {', '.join(sorted(set(sites_with_min)))}"

    for r in all_rows:
        r['comparison_summary'] = comparison

    append_to_excel(all_rows)

    # Print brief summary
    df = pd.DataFrame(all_rows)
    if not df.empty:
        print(df.to_string(index=False))
    print('Summary:', comparison)


if __name__ == '__main__':
    # Use the in-file lists defined above
    samsung_urls_list = SAMSUNG_URLS
    amazon_urls_list = AMAZON_URLS
    output_dir = OUTPUT_DIR

    # Ensure output dir exists before running
    os.makedirs(output_dir, exist_ok=True)

    asyncio.run(main(samsung_urls_list, amazon_urls_list, output_dir=output_dir))
