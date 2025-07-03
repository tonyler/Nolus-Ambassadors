"""
Streamlit Cloud frontend - Submit tweets and view leaderboard only
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import time
from update_service import UpdateService

@st.cache_resource
def get_update_service():
    return UpdateService()

service = get_update_service()

st.set_page_config(
    page_title="Ambassador Dashboard",
    page_icon="🚀",
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
    "📊 Leaderboard", 
    "⏳ Update"
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
            st.rerun()
    
    with st.spinner("Loading leaderboard..."):
        leaderboard = service.get_leaderboard()
    
    if leaderboard:
        total_impressions = sum([amb['total_impressions'] for amb in leaderboard])
        total_tweets = sum([amb['tweets'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Final Impressions", f"{total_impressions:,}")
        with col2:
            st.metric("Tweets with Final Metrics", total_tweets)
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
            'tweets': 'Tweets',
            'total_impressions': 'Total Impressions',
            'total_likes': 'Total Likes',
            'total_replies': 'Total Replies',
            'total_retweets': 'Total Retweets'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info("🎉 **All metrics successfully collected!**")
        
    else:
        st.info("📝 **No leaderboard data yet!**")

elif page == "⏳ Update":
    st.title("⏳ Update Status")
    
    if st.button("Load", type="primary", use_container_width=True):
        with st.spinner("Loading update data..."):
            stats = service.get_update_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tweets", stats['total_tweets'])
        with col2:
            st.metric("Under 3 Days", stats['tweets_under_3_days'])
        with col3:
            st.metric("Ready for Update", stats['tweets_ready_for_update'])
        with col4:
            st.metric("Updated", stats['tweets_updated'])
        