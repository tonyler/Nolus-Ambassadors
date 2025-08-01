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

# Clear cache on app restart to ensure latest code is loaded
if 'service_initialized' not in st.session_state:
    st.cache_resource.clear()
    st.session_state.service_initialized = True

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
    "🟠 Reddit Leaderboard",
    "🏆 Total Leaderboard"
])

if page == "✨ Submit Content":
    st.title("✍️ Submit New Content")
    
    with st.form("content_form"):
        ambassador = st.selectbox("Ambassador", [
            "Tony", "Emlanis", "MonsieurPl4nche", "Martinezz", 
            "Beltein", "Odi", "Frifalin", "BlackOwl"
        ])
        content_url = st.text_input("Content URL")
        
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

    # Month selection
    available_months = service.get_available_months()
    current_month = datetime.now()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if available_months:
            month_options = []
            month_values = []
            
            # Add current month option
            current_option = f"{current_month.strftime('%B %Y')} (Current)"
            month_options.append(current_option)
            month_values.append((current_month.year, current_month.month))
            
            # Add historical months
            for year, month in available_months:
                if not (year == current_month.year and month == current_month.month):
                    month_name = datetime(year, month, 1).strftime('%B %Y')
                    month_options.append(month_name)
                    month_values.append((year, month))
            
            selected_index = st.selectbox("Select Month:", range(len(month_options)), 
                                        format_func=lambda x: month_options[x], 
                                        key="month_select_x")
            selected_year, selected_month = month_values[selected_index]
        else:
            selected_year, selected_month = current_month.year, current_month.month
            st.info("No historical data available")
    
    with col3:
        if st.button("🔄 Refresh", key="refresh_x"):
            print("🔄 Refresh button clicked - reloading X leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading X leaderboard..."):
        print("📊 Loading X leaderboard data from database...")
        leaderboard_result = service.get_leaderboard(selected_year, selected_month)
        
        # Handle the new return format (leaderboard, total_impressions_all)
        if isinstance(leaderboard_result, tuple):
            leaderboard, total_impressions_all = leaderboard_result
        else:
            # Fallback for old format
            leaderboard = leaderboard_result
            total_impressions_all = sum([amb['total_impressions'] for amb in leaderboard]) if leaderboard else 0
        
        print(f"✅ X Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with final metrics")
    
    if leaderboard:
        total_posts = sum([amb['tweets'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Impressions", f"{total_impressions_all:,}")
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
        selected_month_name = datetime(selected_year, selected_month, 1).strftime("%B %Y")
        st.subheader(f"📊 Daily Impression Gains - {selected_month_name}")
        
        # Get daily impressions data for selected month
        try:
            daily_data = service.get_daily_impressions_for_month(selected_year, selected_month)
            
            # Create date range for entire month (1st to last day)
            from calendar import monthrange
            last_day = monthrange(selected_year, selected_month)[1]
            
            start_date = datetime(selected_year, selected_month, 1).date()
            end_date = datetime(selected_year, selected_month, last_day).date()
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
                if selected_year == datetime.now().year and selected_month == datetime.now().month:
                    st.info("No daily impression data yet. Click 'Calculate Today' to start tracking!")
                else:
                    st.info(f"No daily impression data available for {selected_month_name}")
                
        except Exception as e:
            st.info("Chart data temporarily unavailable")
        
    else:
        st.info("📝 **No X leaderboard data yet!**")

elif page == "🟠 Reddit Leaderboard":
    st.title("Reddit Leaderboard")
    
    # Month selection
    available_months = service.get_available_months()
    current_month = datetime.now()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if available_months:
            month_options = []
            month_values = []
            
            # Add current month option
            current_option = f"{current_month.strftime('%B %Y')} (Current)"
            month_options.append(current_option)
            month_values.append((current_month.year, current_month.month))
            
            # Add historical months
            for year, month in available_months:
                if not (year == current_month.year and month == current_month.month):
                    month_name = datetime(year, month, 1).strftime('%B %Y')
                    month_options.append(month_name)
                    month_values.append((year, month))
            
            selected_index = st.selectbox("Select Month:", range(len(month_options)), 
                                        format_func=lambda x: month_options[x], 
                                        key="month_select_reddit")
            selected_year, selected_month = month_values[selected_index]
        else:
            selected_year, selected_month = current_month.year, current_month.month
            st.info("No historical data available")
    
    with col3:
        if st.button("🔄 Refresh", key="refresh_reddit"):
            print("🔄 Refresh button clicked - reloading Reddit leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading Reddit leaderboard..."):
        print("📊 Loading Reddit leaderboard data from database...")
        leaderboard = service.get_reddit_leaderboard(selected_year, selected_month)
        print(f"✅ Reddit Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with final metrics")
    
    if leaderboard:
        total_score = sum([amb['total_score'] for amb in leaderboard])
        total_posts = sum([amb['posts'] for amb in leaderboard])
        total_comments = sum([amb['total_comments'] for amb in leaderboard])
        total_views = sum([amb['total_views'] for amb in leaderboard])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Score", f"{total_score:,}")
        with col2:
            st.metric("Total Posts", total_posts)
        with col3:
            st.metric("Total Comments", f"{total_comments:,}")
        with col4:
            st.metric("Total Views", f"{total_views:,}")
        
        st.divider()
        
        df = pd.DataFrame(leaderboard)
        df['total_score'] = df['total_score'].apply(lambda x: f"{x:,}")
        df['total_comments'] = df['total_comments'].apply(lambda x: f"{x:,}")
        df['total_views'] = df['total_views'].apply(lambda x: f"{x:,}")
        
        df = df.rename(columns={
            'name': 'Ambassador',
            'posts': 'Posts',
            'total_score': 'Score',
            'total_comments': 'Total Comments',
            'total_views': 'Total Views'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.info("📝 **No Reddit leaderboard data yet!**")

elif page == "🏆 Total Leaderboard":
    st.title("Total Leaderboard (Views)")
    
    # Month selection
    available_months = service.get_available_months()
    current_month = datetime.now()
    
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if available_months:
            month_options = []
            month_values = []
            
            # Add current month option
            current_option = f"{current_month.strftime('%B %Y')} (Current)"
            month_options.append(current_option)
            month_values.append((current_month.year, current_month.month))
            
            # Add historical months
            for year, month in available_months:
                if not (year == current_month.year and month == current_month.month):
                    month_name = datetime(year, month, 1).strftime('%B %Y')
                    month_options.append(month_name)
                    month_values.append((year, month))
            
            selected_index = st.selectbox("Select Month:", range(len(month_options)), 
                                        format_func=lambda x: month_options[x], 
                                        key="month_select_total")
            selected_year, selected_month = month_values[selected_index]
        else:
            selected_year, selected_month = current_month.year, current_month.month
            st.info("No historical data available")
    
    with col3:
        if st.button("🔄 Refresh", key="refresh_total"):
            print("🔄 Refresh button clicked - reloading Total leaderboard data...")
            st.rerun()
    
    with st.spinner("Loading Total leaderboard..."):
        print("📊 Loading Total leaderboard data from database...")
        leaderboard = service.get_total_leaderboard(selected_year, selected_month)
        print(f"✅ Total Leaderboard loaded - Found {len(leaderboard) if leaderboard else 0} ambassadors with combined metrics")
    
    if leaderboard:
        total_x_views = sum([amb['x_views'] for amb in leaderboard])
        total_reddit_views = sum([amb['reddit_views'] for amb in leaderboard])
        total_combined_views = sum([amb['total_views'] for amb in leaderboard])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total X Views", f"{total_x_views:,}")
        with col2:
            st.metric("Total Reddit Views", f"{total_reddit_views:,}")
        with col3:
            st.metric("Total Combined Views", f"{total_combined_views:,}")
        
        st.divider()
        
        df = pd.DataFrame(leaderboard)
        df['x_views'] = df['x_views'].apply(lambda x: f"{x:,}")
        df['reddit_views'] = df['reddit_views'].apply(lambda x: f"{x:,}")
        df['total_views'] = df['total_views'].apply(lambda x: f"{x:,}")
        
        df = df.rename(columns={
            'name': 'Ambassador',
            'x_views': 'X Views',
            'reddit_views': 'Reddit Views',
            'total_views': 'Total Views'
        })
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    else:
        st.info("📝 **No total leaderboard data yet!**")