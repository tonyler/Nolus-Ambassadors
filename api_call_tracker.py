# API Call Tracker for Ambassador Dashboard
# Tracks X API usage without consuming API calls

import json
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import subprocess
import sys
from datetime import datetime, timedelta
import calendar

# Add this new file constant
API_USAGE_FILE = "api_usage_log.json"

def load_tweets_data():
    """Load all tweets data from JSON file - needed for tracker functions"""
    try:
        if os.path.exists("tweets_data.json"):
            with open("tweets_data.json", 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        if 'st' in globals():
            st.error(f"Error loading tweets data: {e}")
        else:
            print(f"Error loading tweets data: {e}")
        return {}

def log_api_call(endpoint="tweets", success=True, tweet_count=1):
    """Log an API call to track monthly usage"""
    try:
        # Load existing log
        if os.path.exists(API_USAGE_FILE):
            with open(API_USAGE_FILE, 'r') as f:
                usage_log = json.load(f)
        else:
            usage_log = {}
        
        # Get current month key (e.g., "2025-07")
        current_month = datetime.now().strftime("%Y-%m")
        
        if current_month not in usage_log:
            usage_log[current_month] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "tweets_updated": 0,
                "calls_by_date": {},
                "month_start": datetime.now().replace(day=1).isoformat(),
                "month_end": (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            }
        
        # Log this call
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in usage_log[current_month]["calls_by_date"]:
            usage_log[current_month]["calls_by_date"][today] = {
                "calls": 0,
                "tweets_updated": 0,
                "timestamps": []
            }
        
        # Update counters
        usage_log[current_month]["total_calls"] += 1
        usage_log[current_month]["calls_by_date"][today]["calls"] += 1
        usage_log[current_month]["calls_by_date"][today]["timestamps"].append(datetime.now().isoformat())
        
        if success:
            usage_log[current_month]["successful_calls"] += 1
            usage_log[current_month]["tweets_updated"] += tweet_count
            usage_log[current_month]["calls_by_date"][today]["tweets_updated"] += tweet_count
        else:
            usage_log[current_month]["failed_calls"] += 1
        
        # Save updated log
        with open(API_USAGE_FILE, 'w') as f:
            json.dump(usage_log, f, indent=2)
        
        return True
    except Exception as e:
        if 'st' in globals():
            st.error(f"Error logging API call: {e}")
        else:
            print(f"Error logging API call: {e}")
        return False

def get_monthly_api_usage():
    """Get current month's API usage without making any API calls"""
    try:
        if not os.path.exists(API_USAGE_FILE):
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "tweets_updated": 0,
                "remaining_calls": 100,
                "daily_breakdown": []
            }
        
        with open(API_USAGE_FILE, 'r') as f:
            usage_log = json.load(f)
        
        current_month = datetime.now().strftime("%Y-%m")
        
        if current_month not in usage_log:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "tweets_updated": 0,
                "remaining_calls": 100,
                "daily_breakdown": []
            }
        
        month_data = usage_log[current_month]
        
        # Create daily breakdown for visualization
        daily_breakdown = []
        for date, data in month_data["calls_by_date"].items():
            daily_breakdown.append({
                "date": date,
                "calls": data["calls"],
                "tweets_updated": data["tweets_updated"]
            })
        
        return {
            "total_calls": month_data["total_calls"],
            "successful_calls": month_data["successful_calls"],
            "failed_calls": month_data["failed_calls"],
            "tweets_updated": month_data["tweets_updated"],
            "remaining_calls": max(0, 100 - month_data["total_calls"]),
            "daily_breakdown": sorted(daily_breakdown, key=lambda x: x["date"])
        }
    
    except Exception as e:
        if 'st' in globals():
            st.error(f"Error getting API usage: {e}")
        else:
            print(f"Error getting API usage: {e}")
        return {"total_calls": 0, "remaining_calls": 100, "daily_breakdown": []}

def estimate_api_calls_needed():
    """Estimate how many API calls would be needed to update all tweets"""
    tweets_data = load_tweets_data()
    total_tweets = sum(len(tweets) for tweets in tweets_data.values())
    return total_tweets

def get_tweets_never_updated():
    """Get list of tweets that have never been updated via API"""
    tweets_data = load_tweets_data()
    never_updated = []
    
    for ambassador_name, tweets in tweets_data.items():
        for tweet in tweets:
            # Check if tweet was only submitted manually (impressions = 0 and no last_updated or last_updated = submitted_date)
            submitted_date = tweet.get('submitted_date', '')
            last_updated = tweet.get('last_updated', submitted_date)
            impressions = tweet.get('impressions', 0)
            
            # If impressions are 0 and never updated, or if last_updated equals submitted_date
            if impressions == 0 or last_updated == submitted_date:
                never_updated.append({
                    'ambassador': ambassador_name,
                    'tweet_id': tweet.get('tweet_id', ''),
                    'tweet_url': tweet.get('tweet_url', ''),
                    'submitted_date': submitted_date
                })
    
    return never_updated

def get_priority_tweets_for_update(limit=50):
    """Get priority tweets for API update (oldest first, never updated first)"""
    never_updated = get_tweets_never_updated()
    
    # Sort by submission date (oldest first)
    never_updated.sort(key=lambda x: x['submitted_date'])
    
    return never_updated[:limit]

# Enhanced API Settings Page Section
def show_enhanced_api_usage():
    """Enhanced API usage display for the settings page"""
    
    st.subheader("📊 Monthly API Usage Tracker")
    
    # Get usage data
    usage_data = get_monthly_api_usage()
    
    # Current month summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Calls This Month", 
            usage_data["total_calls"],
            delta=f"Limit: 100"
        )
    
    with col2:
        st.metric(
            "Remaining Calls", 
            usage_data["remaining_calls"],
            delta=f"-{usage_data['total_calls']}" if usage_data["total_calls"] > 0 else "0"
        )
    
    with col3:
        st.metric(
            "Success Rate", 
            f"{(usage_data['successful_calls'] / max(1, usage_data['total_calls']) * 100):.1f}%"
        )
    
    with col4:
        st.metric(
            "Tweets Updated", 
            usage_data["tweets_updated"]
        )
    
    # Usage warning
    if usage_data["total_calls"] >= 90:
        st.error("⚠️ Critical: You've used 90+ API calls this month!")
    elif usage_data["total_calls"] >= 75:
        st.warning("⚠️ Warning: You've used 75+ API calls this month!")
    elif usage_data["total_calls"] >= 50:
        st.info("ℹ️ You've used 50+ API calls this month.")
    
    # Strategy recommendations
    st.subheader("💡 API Strategy")
    
    never_updated = get_tweets_never_updated()
    total_tweets = estimate_api_calls_needed()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Situation:**")
        st.write(f"📊 Total tweets in database: {total_tweets}")
        st.write(f"🔄 Never updated via API: {len(never_updated)}")
        st.write(f"📈 API calls remaining: {usage_data['remaining_calls']}")
    
    with col2:
        st.write("**Recommendations:**")
        if len(never_updated) > usage_data["remaining_calls"]:
            st.warning(f"⚠️ You have {len(never_updated)} tweets to update but only {usage_data['remaining_calls']} calls left")
            st.write("💡 **Strategy**: Update priority tweets first (oldest/most important)")
        else:
            st.success(f"✅ You can update all remaining tweets with {usage_data['remaining_calls']} calls")
    
    # Priority tweets list
    if len(never_updated) > 0:
        st.subheader(f"🎯 Priority Tweets to Update ({len(never_updated)} total)")
        
        priority_tweets = get_priority_tweets_for_update(min(20, usage_data["remaining_calls"]))
        
        if priority_tweets:
            st.write(f"**Next {len(priority_tweets)} tweets to update (oldest first):**")
            
            priority_df = pd.DataFrame(priority_tweets)
            priority_df['submitted_date'] = pd.to_datetime(priority_df['submitted_date']).dt.strftime('%b %d, %Y')
            
            st.dataframe(
                priority_df[['ambassador', 'submitted_date', 'tweet_url']].rename(columns={
                    'ambassador': 'Ambassador',
                    'submitted_date': 'Submitted',
                    'tweet_url': 'Tweet URL'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    # Daily usage chart
    if usage_data["daily_breakdown"]:
        st.subheader("📈 Daily API Usage This Month")
        
        daily_df = pd.DataFrame(usage_data["daily_breakdown"])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        fig = px.bar(
            daily_df,
            x='date',
            y='calls',
            title='API Calls by Day',
            labels={'calls': 'API Calls', 'date': 'Date'}
        )
        st.plotly_chart(fig, use_container_width=True)

# Modified run_x_collector function with logging
def run_x_collector_with_logging():
    """Run the external X API collector script with usage logging"""
    try:
        # Log that we're about to make API calls
        tweets_to_update = estimate_api_calls_needed()
        
        # Show warning if we're going to exceed limits
        usage_data = get_monthly_api_usage()
        if usage_data["remaining_calls"] < tweets_to_update:
            return False, f"⚠️ Cannot proceed: Need {tweets_to_update} calls but only have {usage_data['remaining_calls']} remaining"
        
        # Run the collector script
        result = subprocess.run([sys.executable, "x_collector.py"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True, "✅ Data collection completed successfully!"
        else:
            return False, f"❌ Collection failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "❌ Collection timed out (took more than 5 minutes)"
    except FileNotFoundError:
        return False, "❌ x_collector.py not found. Make sure it's in the same directory."
    except Exception as e:
        return False, f"❌ Error running collector: {e}"