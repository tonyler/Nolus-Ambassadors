"""
Streamlit Cloud frontend - Submit tweets and view leaderboard only
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
from update_service import UpdateService

@st.cache_resource
def get_update_service():
    return UpdateService()

service = get_update_service()

st.set_page_config(
    page_title="Ambassador Dashboard",
    page_icon="img/nolus.png",
    layout="wide"
)

# Sidebar with logo
try:
    col1, col2, col3 = st.sidebar.columns([1, 2, 1])
    with col2:
        st.image("img/nolus.png", width=80)
except:
    st.sidebar.write("🚀")

page = st.sidebar.selectbox("Navigation", [
    "➕ Submit Tweet", 
    "📊 Leaderboard"
])

if page == "➕ Submit Tweet":
    st.title("✍️ Submit New Content")
    
    with st.form("tweet_form"):
        ambassador = st.selectbox("Ambassador", [
            "Tony", "Emlanis", "MonsieurPl4nche", "Martinezz", 
            "Beltein", "Odi", "Frifalin", "BlackOwl"
        ])
        tweet_url = st.text_input("Tweet URL", placeholder="https://x.com/username/status/1234567890")
        
        if st.form_submit_button("Submit Tweet"):
            if tweet_url:
                with st.spinner("Adding tweet to database..."):
                    success, message = service.add_new_tweet(ambassador, tweet_url)
                if success:
                    st.success(f"✅ {message}")
                    time.sleep(3)  # Show success for 3 seconds
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("Please enter a tweet URL")

elif page == "📊 Leaderboard":
    st.title("📊 Ambassador Leaderboard")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh"):
            print("🔄 Refresh button clicked - reloading leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading leaderboard..."):
        print("📊 Loading leaderboard data from database...")
        leaderboard = service.get_leaderboard()
        print(f"✅ Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with final metrics")
    
    if leaderboard:
        total_impressions = sum([amb['total_impressions'] for amb in leaderboard])
        total_tweets = sum([amb['tweets'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Impressions", f"{total_impressions:,}")
        with col2:
            st.metric("Posts Updated Metrics", total_tweets)
        with col3:
            st.metric("Active Ambassadors", len(leaderboard))
        
        st.divider()
        
        df = pd.DataFrame(leaderboard)
        df['total_impressions'] = df['total_impressions'].apply(lambda x: f"{x:,}")
        df['total_likes'] = df['total_likes'].apply(lambda x: f"{x:,}")
        df['total_replies'] = df['total_replies'].apply(lambda x: f"{x:,}")
        df['total_retweets'] = df['total_retweets'].apply(lambda x: f"{x:,}")
        
        df = df.rename(columns={
            'name': 'Ambassador',
            'tweets': 'Posts',
            'total_impressions': 'Total Impressions',
            'total_likes': 'Total Likes',
            'total_replies': 'Total Replies',
            'total_retweets': 'Total Retweets'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.info("📝 **No leaderboard data yet!**")