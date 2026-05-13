from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from fastapi.responses import FileResponse

import random
import time
import pandas as pd

from playwright.sync_api import sync_playwright

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "IPL Ultimate Data API 🚀"}

class ScrapeRequest(BaseModel):
    urls: List[str]

# ---------------- DELAY ----------------
def random_delay(min_s=3, max_s=6):
    time.sleep(random.uniform(min_s, max_s))

def simulate_scroll(page):
    for _ in range(random.randint(3, 5)):
        page.mouse.wheel(0, random.randint(400, 900))
        time.sleep(random.uniform(1, 2))

# ---------------- SCRAPER ----------------
def scrape_player(page, url):

    rows_data = []

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")

        random_delay()
        simulate_scroll(page)
        random_delay()

        # ---------------- NAME + NATIONALITY ----------------
        try:
            name = page.locator("h1").first.inner_text()
        except:
            name = "N/A"

        try:
            nationality = page.locator(".plyr-name-nationality span").first.inner_text()
        except:
            nationality = "N/A"

        # ---------------- PLAYER OVERVIEW ----------------
        overview_data = {}

        try:
            overview_items = page.locator(".player-overview-detail .grid-items").all()

            for item in overview_items:
                value = item.locator("p").inner_text()
                label = item.locator("span").inner_text()

                overview_data[label] = value
        except:
            pass

        # ---------------- ABOUT ----------------
        try:
            about = page.locator(".ih-td-text p").first.inner_text()
        except:
            about = "N/A"

        # ---------------- TABLES ----------------
        tables = page.locator("table.sm-pp-table").all()

        for index, table in enumerate(tables):

            table_type = "Batting" if index == 0 else "Bowling"

            table_rows = table.locator("tbody tr").all()

            for row in table_rows:
                cols = row.locator("td").all_inner_texts()

                # ---------------- BATTING ----------------
                if table_type == "Batting" and len(cols) >= 14:
                    data = {
                        "Name": name,
                        "Nationality": nationality,
                        "Type": "Batting",
                        "Year": cols[0],
                        "Matches": cols[1],
                        "NotOut": cols[2],
                        "Runs": cols[3],
                        "HighScore": cols[4],
                        "Average": cols[5],
                        "BallsFaced": cols[6],
                        "StrikeRate": cols[7],
                        "100s": cols[8],
                        "50s": cols[9],
                        "4s": cols[10],
                        "6s": cols[11],
                        "Catches": cols[12],
                        "Stumpings": cols[13],

                        # Overview fields
                        "IPL Debut": overview_data.get("IPL Debut", ""),
                        "Specialization": overview_data.get("Specialization", ""),
                        "DOB": overview_data.get("Date of Birth", ""),
                        "Total Matches": overview_data.get("Matches", ""),

                        "About": about
                    }
                    rows_data.append(data)

                # ---------------- BOWLING ----------------
                elif table_type == "Bowling" and len(cols) >= 11:
                    data = {
                        "Name": name,
                        "Nationality": nationality,
                        "Type": "Bowling",
                        "Year": cols[0],
                        "Matches": cols[1],
                        "Balls": cols[2],
                        "RunsGiven": cols[3],
                        "Wickets": cols[4],
                        "BestBowling": cols[5],
                        "Average": cols[6],
                        "Economy": cols[7],
                        "StrikeRate": cols[8],
                        "4W": cols[9],
                        "5W": cols[10],

                        # Overview fields
                        "IPL Debut": overview_data.get("IPL Debut", ""),
                        "Specialization": overview_data.get("Specialization", ""),
                        "DOB": overview_data.get("Date of Birth", ""),
                        "Total Matches": overview_data.get("Matches", ""),

                        "About": about
                    }
                    rows_data.append(data)

        return rows_data

    except Exception as e:
        return [{
            "url": url,
            "error": str(e)
        }]

# ---------------- MAIN API ----------------
@app.post("/scrape-data")
def scrape_data(req: ScrapeRequest):

    urls = req.urls[:3]

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0",
            viewport={"width": 1366, "height": 768},
            locale="en-IN"
        )

        page = context.new_page()

        page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        """)

        # Build session
        page.goto("https://www.iplt20.com", timeout=60000)
        time.sleep(random.uniform(4, 6))

        file_name = "ipl_multi_players.xlsx"

        # 🔥 MULTI-SHEET EXCEL
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:

            for i, url in enumerate(urls):
                print(f"Processing {i+1}/{len(urls)}")

                player_data = scrape_player(page, url)

                if not player_data:
                    continue

                df = pd.DataFrame(player_data)

                # ✅ sheet name = player name
                try:
                    player_name = df.iloc[0]["Name"]
                except:
                    player_name = f"Player_{i+1}"

                # Excel limit fix
                player_name = player_name[:30]

                df.to_excel(writer, sheet_name=player_name, index=False)

                # human delay
                if i < len(urls) - 1:
                    time.sleep(random.uniform(8, 12))

        browser.close()

    return FileResponse(
        path=file_name,
        filename=file_name,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )