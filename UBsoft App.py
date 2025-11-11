import streamlit as st
import requests
import pandas as pd
import json
import time
from io import BytesIO

# ================== CONFIG ==================
st.set_page_config(page_title="Ubisoft Job Scraper", layout="centered")
st.title("🎮 Ubisoft Job Scraper")

ALGOLIA_URL = (
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


# ================== FUNCTIONS ==================
@st.cache_data(ttl=3600)
def get_available_countries():
    """Fetch list of available country codes with job counts."""
    payload = {
        "requests": [
            {
                "indexName": "jobs_en-us_default",
                "params": "facets=countryCode&hitsPerPage=0"
            }
        ]
    }
    resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=payload)
    data = resp.json()
    facets = data["results"][0]["facets"]["countryCode"]
    countries = {k: v for k, v in sorted(facets.items(), key=lambda x: -x[1])}
    return countries


def fetch_jobs(country_code=None, keyword=None, page=0, hits_per_page=50):
    """Fetch jobs for one country and keyword."""
    filters = ""
    if country_code:
        filters = f"&facetFilters=[['countryCode:{country_code}']]"
    if keyword is None:
        keyword = ""
    params = f"hitsPerPage={hits_per_page}&page={page}&query={keyword}{filters}"

    payload = {"requests": [{"indexName": "jobs_en-us_default", "params": params}]}
    resp = requests.post(ALGOLIA_URL, headers=HEADERS, json=payload)
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return []
    return results[0].get("hits", [])


def extract_all_jobs(countries, keyword):
    """Loop through selected countries, fetch all jobs."""
    all_jobs = []
    progress = st.progress(0)
    total = len(countries)

    for i, code in enumerate(countries):
        st.write(f"Fetching jobs for **{code.upper()}**...")
        page = 0
        while True:
            jobs = fetch_jobs(country_code=code, keyword=keyword, page=page)
            if not jobs:
                break
            all_jobs.extend(jobs)
            if len(jobs) < 50:
                break
            page += 1
            time.sleep(0.5)

        progress.progress((i + 1) / total)

    progress.empty()
    return all_jobs


# ================== UI INPUTS ==================
countries_dict = get_available_countries()
country_options = list(countries_dict.keys())

keyword = st.text_input("🔍 Enter job title keyword (or leave blank for all):", "")
selected_countries = st.multiselect(
    "🌍 Select countries to scrape:",
    options=country_options,
    default=country_options,
    format_func=lambda x: f"{x.upper()} ({countries_dict[x]} jobs)"
)

if st.button("Start Scraping"):
    if not selected_countries:
        st.warning("Please select at least one country.")
        st.stop()

    with st.spinner("Scraping Ubisoft jobs..."):
        jobs = extract_all_jobs(selected_countries, keyword.strip() or None)

    if jobs:
        df = pd.DataFrame(jobs)
        st.success(f"✅ Scraped {len(df)} jobs from Ubisoft.")
        st.dataframe(df.head(20))

        # Save to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Ubisoft_Jobs")
        st.download_button(
            label="📥 Download Excel file",
            data=output.getvalue(),
            file_name="ubisoft_jobs.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("No jobs found for the selected filters.")
