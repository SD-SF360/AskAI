import requests
from bs4 import BeautifulSoup


def get_ipl_points_table():

    url="https://www.espncricinfo.com/series/indian-premier-league-ipl-2024-1410320/points-table-standings"

    try:

        r=requests.get(url,timeout=20)

        soup=BeautifulSoup(r.text,"html.parser")

        rows=soup.select("table tbody tr")

        table=[]

        for row in rows[:10]:

            cols=row.find_all("td")

            team=cols[0].text.strip()
            pts=cols[7].text.strip()

            table.append({
            "team":team,
            "points":pts
            })

        return table

    except:

        return []