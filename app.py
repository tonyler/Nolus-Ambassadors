"""
Streamlit Cloud frontend - Submit content and view X/Reddit leaderboards
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    "✨ Submit Content", 
    "🐦 X Leaderboard",
    "🟠 Reddit Leaderboard"
])

if page == "✨ Submit Content":
    st.title("✍️ Submit New Content")
    
    with st.form("content_form"):
        ambassador = st.selectbox("Ambassador", [
            "Tony", "Emlanis", "MonsieurPl4nche", "Martinezz", 
            "Beltein", "Odi", "Frifalin", "BlackOwl"
        ])
        content_url = st.text_input("Content URL", placeholder="https://x.com/username/status/1234567890 or https://reddit.com/r/subreddit/comments/...")
        
        if st.form_submit_button("Submit Content"):
            if content_url:
                with st.spinner("Adding content to database..."):
                    success, message = service.add_content(ambassador, content_url)
                if success:
                    st.success(f"✅ {message}")
                    time.sleep(3)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("Please enter a content URL")

elif page == "🐦 X Leaderboard":
    st.title("X Leaderboard")

    # Auto-calculate daily impressions on page load (smart - only when needed)
    try:
        success, message = service.auto_calculate_daily_impressions()
        if success:
            print(f"📊 Auto-calculated daily impressions: {message}")
        else:
            print(f"⚠️ Daily impressions calculation issue: {message}")
    except Exception as e:
        print(f"⚠️ Error in auto-calculation: {e}")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_x"):
            print("🔄 Refresh button clicked - reloading X leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading X leaderboard..."):
        print("📊 Loading X leaderboard data from database...")
        leaderboard = service.get_leaderboard()
        print(f"✅ X Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with final metrics")
    
    if leaderboard:
        total_impressions = sum([amb['total_impressions'] for amb in leaderboard])
        total_posts = sum([amb['tweets'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Impressions", f"{total_impressions:,}")
        with col2:
            st.metric("Total Posts", total_posts)
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
            'total_retweets': 'Total Reposts'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Add impressions gained per day graph
        st.divider()
        current_month = datetime.now().strftime("%B %Y")
        st.subheader(f"📊 Daily Impression Gains - {current_month}")
        
        # Add manual calculation buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("🔄 Calculate Today", key="calc_daily"):
                with st.spinner("Calculating daily impressions..."):
                    success, message = service.calculate_daily_impressions()
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
                    time.sleep(1)
                    st.rerun()
        with col3:
            if st.button("🔄 Reset Today", key="reset_daily"):
                with st.spinner("Resetting today to baseline..."):
                    success, message = service.reset_today_impressions()
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
                    time.sleep(1)
                    st.rerun()
        
        # Get daily impressions data for current month
        try:
            daily_data = service.get_daily_impressions_for_month()
            
            # Create date range for entire month (1st to last day)
            from calendar import monthrange
            year = datetime.now().year
            month = datetime.now().month
            last_day = monthrange(year, month)[1]
            
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, last_day).date()
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Create complete DataFrame with all days of the month
            complete_data = pd.DataFrame(index=date_range.date)
            complete_data['Daily Impressions Gained'] = 0
            complete_data.index.name = 'Date'
            
            # Fill in actual data
            if daily_data:
                for record in daily_data:
                    record_date = datetime.fromisoformat(record['date']).date()
                    if record_date in complete_data.index:
                        complete_data.loc[record_date, 'Daily Impressions Gained'] = record['impressions_gained']
            
            # Create line chart
            st.line_chart(complete_data)
            
            # Show summary stats
            if daily_data:
                total_gained = sum([record['impressions_gained'] for record in daily_data])
                avg_daily = total_gained / len(daily_data) if daily_data else 0
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Gained This Month", f"{total_gained:,}")
                with col2:
                    st.metric("Average Daily Gain", f"{avg_daily:,.0f}")
                with col3:
                    st.metric("Days Tracked", len(daily_data))
            else:
                st.info("No daily impression data yet. Click 'Calculate Today' to start tracking!")
                
        except Exception as e:
            st.info("Chart data temporarily unavailable")
        
    else:
        st.info("📝 **No X leaderboard data yet!**")

elif page == "🟠 Reddit Leaderboard":
    st.title("Reddit Leaderboard")    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", key="refresh_reddit"):
            print("🔄 Refresh button clicked - reloading Reddit leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading Reddit leaderboard..."):
        print("📊 Loading Reddit leaderboard data from database...")
        leaderboard = service.get_reddit_leaderboard()
        print(f"✅ Reddit Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with final metrics")
    
    if leaderboard:
        total_score = sum([amb['total_score'] for amb in leaderboard])
        total_posts = sum([amb['posts'] for amb in leaderboard])
        total_comments = sum([amb['total_comments'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Score", f"{total_score:,}")
        with col2:
            st.metric("Total Posts", total_posts)
        with col3:
            st.metric("Total Comments", f"{total_comments:,}")
        
        st.divider()
        
        df = pd.DataFrame(leaderboard)
        df['total_score'] = df['total_score'].apply(lambda x: f"{x:,}")
        df['total_comments'] = df['total_comments'].apply(lambda x: f"{x:,}")
        
        df = df.rename(columns={
            'name': 'Ambassador',
            'posts': 'Posts',
            'total_score': 'Score',
            'total_comments': 'Total Comments'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.info("📝 **No Reddit leaderboard data yet!**")