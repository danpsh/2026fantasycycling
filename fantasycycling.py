import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="2026 Fantasy Cycling", layout="wide")
st.title("🚴 2026 Fantasy Cycling Leaderboard")
st.markdown("Automated leaderboard using live results from ProCyclingStats.")

# --- DATA LOADING WITH ENCODING FIX ---
@st.cache_data
def load_local_data():
    # 'utf-8-sig' handles files saved by Excel that include a Byte Order Mark (BOM)
    # 'latin1' is a fallback if your file uses standard Windows encoding
    try:
        riders_df = pd.read_csv('riders.csv', encoding='utf-8-sig')
        scoring_df = pd.read_csv('scoringrules.csv', encoding='utf-8-sig')
        races_df = pd.read_csv('races2025.csv', encoding='utf-8-sig')
        return riders_df, scoring_df, races_df
    except UnicodeDecodeError:
        # If utf-8-sig fails, try latin1 for different character sets
        riders_df = pd.read_csv('riders.csv', encoding='latin1')
        scoring_df = pd.read_csv('scoringrules.csv', encoding='latin1')
        races_df = pd.read_csv('races2025.csv', encoding='latin1')
        return riders_df, scoring_df, races_df

riders, scoring, races = load_local_data()

# --- THE PCS SCRAPER ENGINE ---
def get_pcs_results(slug):
    url = f"https://www.procyclingstats.com/{slug}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # PCS results are typically in a table with class 'results'
        table = soup.find('table', {'class': 'results'})
        
        results = []
        if table:
            # We skip the header row and take the top 10 finishers
            rows = table.find_all('tr')[1:11]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 3:
                    rank = cols[0].text.strip()
                    # Name is usually in the 4th column; replace special space characters
                    name = cols[3].text.strip().replace('\xa0', ' ')
                    
                    if rank.isdigit():
                        results.append({'rider_name': name, 'rank': int(rank)})
        return pd.DataFrame(results)
    except Exception as e:
        st.error(f"Error connecting to PCS for {slug}: {e}")
        return pd.DataFrame()

# --- SIDEBAR & REFRESH ---
if st.button('🔄 Sync Live Results from PCS'):
    st.info("Fetching data... this may take a moment depending on the number of races.")
    
    all_results_list = []
    
    # Process each race/stage defined in your races2025.csv
    for index, row in races.iterrows():
        df_stage = get_pcs_results(row['pcs_slug'])
        if not df_stage.empty:
            df_stage['race_name'] = row['race_name']
            all_results_list.append(df_stage)
    
    if all_results_list:
        # Combine all scraped results into one master table
        master_results = pd.concat(all_results_list)
        
        # Merge results with your points system
        results_with_points = master_results.merge(scoring, on='rank')
        
        # Merge with your rider list to link riders to their fantasy owners/teams
        final_leaderboard = results_with_points.merge(riders, on='rider_name')
        
        # --- DISPLAY TABULAR DATA ---
        st.header("🏆 Fantasy Standings")
        
        # Group by the rider name (and team if available) and sum points
        standings = final_leaderboard.groupby(['rider_name', 'team'])['points'].sum().sort_values(ascending=False).reset_index()
        st.table(standings)
        
        with st.expander("Detailed Points Breakdown"):
            st.dataframe(final_leaderboard[['race_name', 'rider_name', 'rank', 'points']])
    else:
        st.warning("No data found. Please check that your PCS slugs are correct.")

else:
    st.write("Click the button above to start the live sync.")
