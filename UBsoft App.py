import streamlit as st
import requests
import pandas as pd
import json
import time

# ================== CONFIG ==================
URL = (
    "https://avcvysejs1-2.algolianet.com/1/indexes/*/queries"
    "?x-algolia-agent=Algolia%20for%20JavaScript%20(4.8.4)%3B%20Browser%20(lite)%3B%20JS%20Helper%20(3.11.0)%3B%20react%20(16.12.0)%3B%20react-instantsearch%20(6.8.3)"
    "&x-algolia-api-key=d2ec5782c4eb549092cfa4ed5062599a"
    "&x-algolia-application-id=AVCVYSEJS1"
)

HEADERS = {
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.ubisoft.com",
    "referer": "https://www.ubisoft.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
}

AVAILABLE_COUNTRIES = [
    "ca", "fr", "cn", "ua", "de", "gb", "ro", "vn",
    "ph", "es", "in", "br", "it", "sg", "us"
]

# ================== FUNCTIONS ==================
def fetch_jobs(country_code, keyword=None):
    jobs = []
    page = 0
    while True:
        params = (
            f"facetFilters=%5B%5B%22countryCode%3A{country_code}%22%5D%5D"
            "&facets=%5B%22jobFamily%22%2C%22team%22%2C%22countryCode%22%2C%22cities%22%2C%22contractType%22%2C%22workFlexibility%22%2C%22graduateProgram%22%5D"
            "&highlightPostTag=%3C%2Fais-highlight-0000000000%3E"
            "&highlightPreTag=%3Cais-highlight-0000000000%3E"
            "&maxValuesPerFacet=100"
            f"&page={page}"
            "&hitsPerPage=50"
            f"&query={keyword or ''}"
        )
        payload = {"requests": [{"indexName": "jobs_en-us_default", "params": params}]}

        resp = requests.post(URL, headers=HEADERS, data=json.dumps(payload))
        if resp.status_code != 200:
            st.warning(f"Failed for {country_code} page {page}: {resp.status_code}")
            break

        data = resp.json()
        hits = data["results"][0].get("hits", [])
        if not hits:
            break

        jobs.extend(hits)
        page += 1
        time.sleep(0.5)  # polite delay

    return jobs

# ================== STREAMLIT UI ==================
st.set_page_config(page_title="LVMH Job Scraper", layout="centered")
st.title("🎮 Ubisoft Job Scraper")

# Country selection
countries = st.multiselect(
    "Select countries (or leave empty for all):",
    options=AVAILABLE_COUNTRIES,
    default=[]
)
keyword = st.text_input("Enter job keyword (optional)")

if st.button("Fetch Jobs"):
    selected_countries = countries if countries else AVAILABLE_COUNTRIES
    all_jobs = []

    progress_bar = st.progress(0)
    total = len(selected_countries)

    for i, country in enumerate(selected_countries, start=1):
        st.info(f"Fetching jobs for {country.upper()}...")
        jobs = fetch_jobs(country, keyword)
        st.success(f"Found {len(jobs)} jobs for {country.upper()}")
        all_jobs.extend(jobs)
        progress_bar.progress(i / total)

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        st.write(f"Total jobs fetched: {len(all_jobs)}")
        st.dataframe(df)

        # Excel download
        excel_file = "ubisoft_jobs.xlsx"
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button(
                label="📥 Download Excel",
                data=f,
                file_name=excel_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("No jobs found for the selected filters.")

