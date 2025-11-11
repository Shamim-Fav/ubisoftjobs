import requests
import pandas as pd
import streamlit as st
import time

# ================== CONFIG ==================
URL = "https://avcvysejs1-2.algolianet.com/1/indexes/*/queries"
HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://www.ubisoft.com",
    "referer": "https://www.ubisoft.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}
ALGOLIA_APP_ID = "AVCVYSEJS1"
ALGOLIA_API_KEY = "d2ec5782c4eb549092cfa4ed5062599a"

HITS_PER_PAGE = 50

# ================== FUNCTIONS ==================
def fetch_jobs(country_code, keyword=None):
    """Fetch jobs from Ubisoft Algolia API with optional keyword."""
    jobs = []
    page = 0
    while True:
        # Build request payload
        payload = {
            "requests": [
                {
                    "indexName": "jobs_en-us_default",
                    "params": (
                        f"facetFilters=[['countryCode:{country_code}']]&"
                        f"facets=[jobFamily,team,countryCode,cities,contractType,workFlexibility,graduateProgram]&"
                        f"hitsPerPage={HITS_PER_PAGE}&page={page}&query={keyword or ''}"
                    )
                }
            ]
        }
        # Send POST request
        try:
            resp = requests.post(
                URL,
                headers=HEADERS,
                params={
                    "x-algolia-agent": "Algolia for JavaScript (4.8.4); Browser (lite); JS Helper (3.11.0); react (16.12.0); react-instantsearch (6.8.3)",
                    "x-algolia-api-key": ALGOLIA_API_KEY,
                    "x-algolia-application-id": ALGOLIA_APP_ID
                },
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Error fetching page {page}: {e}")
            break

        hits = data.get("results", [])[0].get("hits", [])
        if not hits:
            break
        
        jobs.extend(hits)
        st.progress(min((page + 1) / 10, 1.0))  # approximate progress
        page += 1

    return jobs

def extract_job_data(job):
    """Extract relevant fields from a job entry."""
    return {
        "title": job.get("title"),
        "country": job.get("countryCode"),
        "city": ", ".join(job.get("cities", [])),
        "team": job.get("team"),
        "jobFamily": job.get("jobFamily"),
        "contractType": job.get("contractType"),
        "workFlexibility": job.get("workFlexibility"),
        "graduateProgram": job.get("graduateProgram"),
        "experienceLevel": job.get("experienceLevel"),
        "link": job.get("link"),
        "description": job.get("description"),
        "additionalInformation": job.get("additionalInformation"),
        "qualifications": job.get("qualifications")
    }

# ================== STREAMLIT UI ==================
st.set_page_config(page_title="Ubisoft Job Scraper", layout="wide")
st.title("🎮 Ubisoft Job Scraper")

# Inputs
countries_input = st.text_input(
    "Enter country codes (comma-separated) or 'all'",
    value="ca"
)
keyword_input = st.text_input(
    "Enter job keyword (leave blank for all jobs)"
)

if st.button("Fetch Jobs"):
    country_codes = [c.strip().lower() for c in countries_input.split(",")] if countries_input.lower() != "all" else [
        "ca","fr","cn","ua","de","gb","ro","vn","ph","es","in","br","it","sg","us"
    ]
    
    all_jobs = []
    for code in country_codes:
        st.info(f"Fetching jobs for {code.upper()}...")
        jobs = fetch_jobs(code, keyword_input)
        if jobs:
            st.success(f"✅ Fetched {len(jobs)} jobs from {code.upper()}")
            all_jobs.extend([extract_job_data(j) for j in jobs])
        else:
            st.warning(f"No jobs found for {code.upper()}")

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        st.write(f"Total jobs fetched: {len(df)}")
        st.dataframe(df)

        # Excel download
        excel_file = "ubisoft_jobs.xlsx"
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button("📥 Download Excel", f, file_name=excel_file)
    else:
        st.warning("No jobs found for the selected filters.")
