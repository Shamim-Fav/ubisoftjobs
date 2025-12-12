import streamlit as st
import requests
import pandas as pd
import json
import time
import re 
from io import StringIO # Added for CSV conversion

# The UTF-8 Byte Order Mark (BOM) for correct encoding recognition by Excel/other readers
BOM = u'\ufeff' 

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

# Fixed Company Name
FIXED_COMPANY_NAME = 'Ubisoft'

# List of all new columns and their default values (EXCLUDING 'Slug' and 'Company' since they are calculated/fixed)
BLANK_COLUMNS_DEFAULTS = {
    "Collection ID": '', 
    "Locale ID": '', 
    "Item ID": '', 
    "Archived": '', 
    "Draft": '', 
    "Created On": '', 
    "Updated On": '', 
    "Published On": '', 
    "CMS ID": '', 
    "Salary Range": '', 
    "Access": '', 
    "Level": '', 
    "Salary": '', 
    "Deadline": ''
}

# The EXACT serialization order requested for the filtered output
FILTERED_COLUMN_ORDER = [
    "Name", "Slug", "Collection ID", "Locale ID", "Item ID", "Archived", "Draft", 
    "Created On", "Updated On", "Published On", "CMS ID", "Company", "Type", 
    "Description", "Salary Range", "Access", "Location", "Industry", "Level", 
    "Salary", "Deadline", "Apply URL" 
]

# ================== FUNCTIONS ==================

# Helper function to generate the slug
def generate_slug(row):
    name_str = str(row['Name'])
    location_str = str(row['Location'])
    
    company_part = FIXED_COMPANY_NAME
    
    # Job Title (Name) - Take first two words
    title_words = name_str.split()
    title_part = ' '.join(title_words[:2])
    
    location_part = location_str
    
    # Combine the parts
    full_slug = f"{company_part} {title_part} {location_part}"
    
    # Clean up: replace sequences of non-alphanumeric chars with a single hyphen, lowercase, and strip leading/trailing hyphens
    cleaned_slug = re.sub(r'[^a-zA-Z0-9]+', '-', full_slug).strip('-').lower()
    
    return cleaned_slug

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

# Function to convert DataFrame to CSV STRING with BOM
def to_csv_string(df):
    csv_buffer = StringIO()
    # WRITE THE BOM CHARACTER FOR UTF-8 RECOGNITION
    csv_buffer.write(BOM) 
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

# ================== STREAMLIT UI ==================
st.set_page_config(page_title="Ubisoft Job Scraper", layout="centered")
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

        # 1. COLUMN MODIFICATIONS
        rename_map = {
            'title': 'Name',
            'contractType': 'Type',
            'description': 'Description',
            'city': 'Location', 
            'jobFamily': 'Industry',
            'link': 'Apply URL' 
        }
        
        df = df.rename(columns=rename_map)
        
        if 'slug' in df.columns:
            df = df.drop(columns=['slug'])

        # 2. CALCULATE and ADD NEW COLUMNS
        
        df['Company'] = FIXED_COMPANY_NAME
        
        # Add remaining BLANK columns
        for col, default_val in BLANK_COLUMNS_DEFAULTS.items():
            if col not in df.columns:
                 df[col] = default_val

        # Add CALCULATED 'Slug' column
        df['Slug'] = df.apply(generate_slug, axis=1)

        st.write(f"Total jobs fetched: {len(all_jobs)}")
        
        # --- STREAMLIT DISPLAY ---
        display_columns = ['Name', 'Slug', 'Location', 'Industry', 'Type', 'Apply URL']
        
        df_display = df[[col for col in display_columns if col in df.columns]]
        st.dataframe(df_display)
        
        # --- DUAL DOWNLOAD BUTTONS (CSV) ---
        
        # 3. FILTERED DATA DOWNLOAD (CSV)
        filtered_cols_to_select = [col for col in FILTERED_COLUMN_ORDER if col in df.columns]
        df_filtered = df.reindex(columns=filtered_cols_to_select)
        
        # Convert to CSV string with BOM
        filtered_csv_data = to_csv_string(df_filtered)
        
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=filtered_csv_data,
            file_name="ubisoft_jobs_filtered.csv", 
            mime="text/csv" 
        )
        
        # 4. FULL DATA DOWNLOAD (CSV)
        # Convert to CSV string with BOM
        full_csv_data = to_csv_string(df)
        
        st.download_button(
            label="⬇️ Download FULL Data (CSV)",
            data=full_csv_data,
            file_name="ubisoft_jobs_full.csv", 
            mime="text/csv" 
        )

    else:
        st.warning("No jobs found for the selected filters.")

