import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- APP CONFIGURATION ---
st.set_page_config(page_title="2026 Fantasy Cycling", layout="wide")
st.title("🚴 2026 Fantasy Cycling Leaderboard")
st.markdown("Testing 2025 results using live PCS data.")

# --- LOAD DATA ---
# Using exact names from your repository image
try:
    riders = pd.read_csv('riders.csv')
    scoring = pd.read_csv('scoringrules.csv')
    races = pd.read_csv('races2025.csv')
except FileNotFoundError as e:
    st.error(f"Error: Could not find one of your CSV files. Check names: {e}")
    st.stop()

# --- THE SCRAPER ---
@st.cache_data(ttl=3600) # Caches results for 1 hour so it's fast
def get_pcs_stage_results(slug):
    url = f"https://www.procyclingstats.com/{slug}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # PCS stage results are usually in the first table with class 'results'
        table = soup.find('table', {'class': 'results'})
        
        results = []
        if table:
            rows = table.find_all('tr')[1:11] # Get top 10 finishers
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 3:
                    rank = cols[0].text.strip()
                    # Name is usually in the 4th column (index 3)
                    name = cols[3].text.strip().replace('\xa0', ' ')
                    
                    if rank.isdigit():
                        results.append({'rider_name': name, 'rank': int(rank)})
        return pd.DataFrame(results)
    except Exception as e:
        return pd.DataFrame()

# --- MAIN APP LOGIC ---
if st.button('🔄 Refresh & Sync PCS Results'):
    st.cache_data.clear() # Clears old data to get fresh results
    st.info("Scraping live data from PCS... please wait.")
    
    all_stage_data = []
    
    # Loop through each race/stage in your races2025.csv
    for _, row in races.iterrows():
        df_res = get_pcs_stage_results(row['pcs_slug'])
        if not df_res.empty:
            df_res['race'] = row['race_name']
            all_stage_data.append(df_res)
    
    if all_stage_data:
        # 1. Combine all scraped results
        final_results = pd.concat(all_stage_data)
        
        # 2. Attach points from your scoringrules.csv
        merged_points = final_results.merge(scoring, on='rank')
        
        # 3. Match with your rider list to see who owns whom
        leaderboard = merged_points.merge(riders, on='rider_name')
        
        # --- DISPLAY RESULTS ---
        st.header("🏆 Current Leaderboard")
        # Group by rider and sum their points
        summary = leaderboard.groupby(['rider_name', 'team'])['points'].sum().sort_values(ascending=False).reset_index()
        st.table(summary)
        
        with st.expander("View Full Point Breakdown"):
            st.dataframe(leaderboard[['race', 'rider_name', 'rank', 'points']])
    else:
        st.warning("No results found. Check your PCS slugs in races2025.csv.")

else:
    st.write("Click the button above to calculate the latest scores.")
