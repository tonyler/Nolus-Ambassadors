import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import requests
from urllib.parse import urlparse
import time
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import queue
import atexit


# Page configuration
st.set_page_config(
    page_title="Ambassador Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# JSON file paths
AMBASSADORS_FILE = "ambassadors.json"
TWEETS_DATA_FILE = "tweets_data.json"
BACKUP_DIR = "monthly_backups"
CONFIG_FILE = "config.json"

# Global variable for sheet updater process
sheet_updater_process = None

def auto_start_sheet_updater():
    """Automatically start the sheet updater when app starts"""
    global sheet_updater_process
    
    # Check if already running
    if sheet_updater_process and sheet_updater_process.poll() is None:
        return True
    
    try:
        # Start the sheet updater process
        sheet_updater_process = subprocess.Popen(
            [sys.executable, "sheet_updater.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Register cleanup function
        atexit.register(cleanup_sheet_updater)
        
        print(f"🚀 Auto-started sheet updater (PID: {sheet_updater_process.pid})")
        return True
    except Exception as e:
        print(f"❌ Failed to auto-start sheet updater: {e}")
        return False

def cleanup_sheet_updater():
    """Clean up sheet updater process when app exits"""
    global sheet_updater_process
    if sheet_updater_process and sheet_updater_process.poll() is None:
        try:
            sheet_updater_process.terminate()
            sheet_updater_process.wait(timeout=5)
            print("👋 Sheet updater stopped on app exit")
        except:
            pass

# Auto-start the sheet updater when the app loads
if 'sheet_updater_started' not in st.session_state:
    st.session_state.sheet_updater_started = True
    auto_start_sheet_updater()

# Simple API counter functions
def get_api_count():
    """Get current month's API call count"""
    try:
        if os.path.exists("api_count.json"):
            with open("api_count.json", 'r') as f:
                data = json.load(f)
                current_month = datetime.now().strftime("%Y-%m")
                return data.get(current_month, 0)
        return 0
    except:
        return 0

def increment_api_count():
    """Add 1 to API call count"""
    try:
        current_month = datetime.now().strftime("%Y-%m")
        data = {}
        
        if os.path.exists("api_count.json"):
            with open("api_count.json", 'r') as f:
                data = json.load(f)
        
        data[current_month] = data.get(current_month, 0) + 1
        
        with open("api_count.json", 'w') as f:
            json.dump(data, f)
        
        return data[current_month]
    except:
        return 0

def get_tweets_ready_for_update():
    """Get tweets that are 3+ days old and haven't been updated yet"""
    tweets_data = load_tweets_data()
    ready_for_update = []
    
    three_days_ago = datetime.now() - timedelta(days=3)
    
    for ambassador_name, tweets in tweets_data.items():
        for tweet in tweets:
            # Parse submission date
            submitted_date_str = tweet.get('submitted_date', '')
            if not submitted_date_str:
                continue
                
            try:
                submitted_date = datetime.fromisoformat(submitted_date_str)
            except:
                continue
            
            # Check if tweet is 3+ days old
            if submitted_date <= three_days_ago:
                # Check if it's never been updated OR was only updated on submission
                last_updated = tweet.get('last_updated', submitted_date_str)
                impressions = tweet.get('impressions', 0)
                final_update = tweet.get('final_update', False)
                
                # If impressions are 0 or last_updated equals submitted_date, and not marked as final
                if not final_update and (impressions == 0 or last_updated == submitted_date_str):
                    ready_for_update.append({
                        'ambassador': ambassador_name,
                        'tweet_id': tweet.get('tweet_id'),
                        'tweet_url': tweet.get('tweet_url'),
                        'submitted_date': submitted_date_str,
                        'days_old': (datetime.now() - submitted_date).days
                    })
    
    # Sort by oldest first
    ready_for_update.sort(key=lambda x: x['submitted_date'])
    return ready_for_update

def get_smart_update_stats():
    """Get stats about what needs updating"""
    tweets_data = load_tweets_data()
    
    total_tweets = 0
    tweets_under_3_days = 0
    tweets_ready_for_update = 0
    tweets_already_updated = 0
    
    three_days_ago = datetime.now() - timedelta(days=3)
    
    for ambassador_name, tweets in tweets_data.items():
        for tweet in tweets:
            total_tweets += 1
            
            submitted_date_str = tweet.get('submitted_date', '')
            if not submitted_date_str:
                continue
                
            try:
                submitted_date = datetime.fromisoformat(submitted_date_str)
            except:
                continue
            
            if submitted_date > three_days_ago:
                tweets_under_3_days += 1
            else:
                # Check if needs update
                last_updated = tweet.get('last_updated', submitted_date_str)
                impressions = tweet.get('impressions', 0)
                final_update = tweet.get('final_update', False)
                
                if not final_update and (impressions == 0 or last_updated == submitted_date_str):
                    tweets_ready_for_update += 1
                else:
                    tweets_already_updated += 1
    
    return {
        'total_tweets': total_tweets,
        'tweets_under_3_days': tweets_under_3_days,
        'tweets_ready_for_update': tweets_ready_for_update,
        'tweets_already_updated': tweets_already_updated
    }

def start_sheet_updater():
    """Start the sheet updater process (manual override)"""
    global sheet_updater_process
    try:
        if sheet_updater_process and sheet_updater_process.poll() is None:
            return False, "Sheet updater is already running"
        
        sheet_updater_process = subprocess.Popen(
            [sys.executable, "sheet_updater.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True, "Sheet updater started successfully"
    except Exception as e:
        return False, f"Failed to start sheet updater: {e}"

def stop_sheet_updater():
    """Stop the sheet updater process"""
    global sheet_updater_process
    try:
        if sheet_updater_process and sheet_updater_process.poll() is None:
            sheet_updater_process.terminate()
            sheet_updater_process.wait(timeout=5)
            return True, "Sheet updater stopped"
        else:
            return False, "Sheet updater is not running"
    except Exception as e:
        return False, f"Failed to stop sheet updater: {e}"

def is_sheet_updater_running():
    """Check if sheet updater is running"""
    global sheet_updater_process
    if sheet_updater_process and sheet_updater_process.poll() is None:
        return True
    return False

def manual_sheet_update():
    """Trigger a manual sheet update"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", """
import sys
sys.path.append('.')
from sheet_updater import update_sheet
update_sheet()
"""],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "Manual sheet update completed"
        else:
            return False, f"Update failed: {result.stderr}"
    except Exception as e:
        return False, f"Error running manual update: {e}"

def run_smart_x_collector():
    """Run the smart X API collector with real-time output display"""
    try:
        # Create placeholders for real-time output
        st.write("🔄 **Smart Collection Progress:**")
        output_container = st.container()
        
        # Function to read subprocess output
        def read_output(pipe, msg_queue):
            for line in iter(pipe.readline, ''):
                if line:
                    msg_queue.put(line.strip())
            pipe.close()
        
        # Start subprocess with real-time output capture
        process = subprocess.Popen(
            [sys.executable, "x_collector.py", "--smart"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Create queue for messages
        msg_queue = queue.Queue()
        
        # Start thread to read output
        reader_thread = threading.Thread(target=read_output, args=(process.stdout, msg_queue))
        reader_thread.daemon = True
        reader_thread.start()
        
        messages = []
        
        # Display messages in real-time
        while process.poll() is None or not msg_queue.empty():
            try:
                # Get message from queue (non-blocking)
                message = msg_queue.get_nowait()
                messages.append(message)
                
                # Update display with latest messages
                with output_container:
                    for msg in messages[-10:]:  # Show last 10 messages
                        if "✅" in msg or "🎉" in msg:
                            st.success(msg)
                        elif "❌" in msg or "⚠️" in msg:
                            st.error(msg)
                        elif "📡" in msg or "📊" in msg or "📝" in msg:
                            st.info(msg)
                        elif "🧠" in msg or "🚀" in msg:
                            st.write(f"**{msg}**")
                        else:
                            st.text(msg)
                
            except queue.Empty:
                time.sleep(0.1)
        
        # Wait for process completion
        return_code = process.wait()
        
        if return_code == 0:
            return True, "✅ Smart data collection completed successfully!"
        else:
            return False, f"❌ Collection failed with return code: {return_code}"
            
    except subprocess.TimeoutExpired:
        return False, "❌ Collection timed out (took more than 5 minutes)"
    except FileNotFoundError:
        return False, "❌ x_collector.py not found. Make sure it's in the same directory."
    except Exception as e:
        return False, f"❌ Error running collector: {e}"

def show_smart_api_dashboard():
    """Show the smart API management dashboard"""
    st.subheader("🧠 Smart API Management (3-Day Strategy)")
    
    stats = get_smart_update_stats()
    ready_tweets = get_tweets_ready_for_update()
    
    # Status overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tweets", stats['total_tweets'])
    
    with col2:
        st.metric("Under 3 Days", stats['tweets_under_3_days'])
        st.caption("⏳ Waiting for engagement to stabilize")
    
    with col3:
        st.metric("Ready for Update", stats['tweets_ready_for_update'])
        st.caption("🎯 Need their final impression count")
    
    with col4:
        st.metric("Already Updated", stats['tweets_already_updated'])
        st.caption("✅ Have final 3-day data")
    
    # Smart collection button
    if stats['tweets_ready_for_update'] > 0:
        st.success(f"🎯 {stats['tweets_ready_for_update']} tweets are ready for their 3-day update!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"🧠 Update {stats['tweets_ready_for_update']} Ready Tweets", type="primary"):
                
                # Show which tweets will be updated
                st.write("📋 **Tweets to be updated:**")
                for i, tweet in enumerate(ready_tweets[:5], 1):
                    st.text(f"   {i}. {tweet['ambassador']}: {tweet['days_old']} days old")
                if len(ready_tweets) > 5:
                    st.text(f"   ... and {len(ready_tweets) - 5} more")
                
                st.divider()
                
                # Run smart collection with real-time output
                success, message = run_smart_x_collector()
                
                if success:
                    st.success(message)
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            api_count = get_api_count()
            remaining = 100 - api_count
            if stats['tweets_ready_for_update'] <= remaining:
                st.info(f"✅ Within API limits ({stats['tweets_ready_for_update']} calls needed, {remaining} remaining)")
            else:
                st.warning(f"⚠️ Need {stats['tweets_ready_for_update']} calls but only {remaining} remaining")
    else:
        st.info("🕐 No tweets ready for update right now. All tweets are either too new (under 3 days) or already have their final impression counts.")
    
    # Show ready tweets list
    if ready_tweets:
        st.subheader(f"📋 Tweets Ready for 3-Day Update ({len(ready_tweets)})")
        
        ready_df = pd.DataFrame(ready_tweets)
        ready_df['days_old'] = ready_df['days_old'].astype(str) + ' days'
        ready_df['submitted_date'] = pd.to_datetime(ready_df['submitted_date']).dt.strftime('%b %d, %Y')
        
        display_ready_df = ready_df[['ambassador', 'days_old', 'submitted_date']].rename(columns={
            'ambassador': 'Ambassador',
            'days_old': 'Age',
            'submitted_date': 'Submitted'
        })
        
        st.dataframe(display_ready_df, use_container_width=True, hide_index=True)

    # Sheet Updater Status (Now Auto-Running)
    st.subheader("📊 Google Sheets Integration (Auto-Running)")
    
    # Status check
    is_running = is_sheet_updater_running()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_running:
            st.success("🟢 Auto-Updater: Running Every 10 Minutes")
        else:
            st.warning("🟡 Auto-Updater: Stopped (will restart on app reload)")
    
    with col2:
        if st.button("🔄 Manual Update Now", type="secondary"):
            with st.spinner("Updating Google Sheet..."):
                success, message = manual_sheet_update()
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    with col3:
        st.info("💡 Updates every 10 minutes automatically")
    
    # Advanced controls (optional)
    with st.expander("🔧 Advanced Controls"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Restart Auto-Updater", disabled=is_running):
                success, message = start_sheet_updater()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("⏹️ Stop Auto-Updater", disabled=not is_running):
                success, message = stop_sheet_updater()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    st.divider()

def run_manual_x_collector():
    """Run the X API collector for ALL tweets (manual/testing mode)"""
    try:
        # Run the collector script without smart flag (legacy mode)
        result = subprocess.run([sys.executable, "x_collector.py"], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True, "✅ Manual data collection completed successfully!"
        else:
            return False, f"❌ Collection failed: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "❌ Collection timed out (took more than 5 minutes)"
    except FileNotFoundError:
        return False, "❌ x_collector.py not found. Make sure it's in the same directory."
    except Exception as e:
        return False, f"❌ Error running collector: {e}"

def load_config():
    """Load X API configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Create default config file
            default_config = {
                "x_api": {
                    "bearer_token": "YOUR_BEARER_TOKEN_HERE",
                    "api_key": "YOUR_API_KEY_HERE", 
                    "api_secret": "YOUR_API_SECRET_HERE",
                    "access_token": "YOUR_ACCESS_TOKEN_HERE",
                    "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET_HERE"
                },
                "settings": {
                    "auto_fetch_enabled": True,
                    "daily_update_time": "09:00",
                    "max_requests_per_day": 3,
                    "fetch_tweet_fields": ["public_metrics"]
                }
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return {}

def load_ambassadors_from_json():
    """Load ambassador list from JSON file"""
    try:
        if os.path.exists(AMBASSADORS_FILE):
            with open(AMBASSADORS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('ambassadors', [])
        else:
            # Create default file if it doesn't exist
            default_ambassadors = ["Tony", "Emlanis", "Monsieur", "Pl4nche", "Martinezz", "Beltein", "Odi", "Frifalin"]
            save_ambassadors_to_json(default_ambassadors)
            return default_ambassadors
    except Exception as e:
        st.error(f"Error loading ambassadors: {e}")
        return []

def save_ambassadors_to_json(ambassadors_list):
    """Save ambassador list to JSON file"""
    try:
        data = {"ambassadors": ambassadors_list}
        with open(AMBASSADORS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving ambassadors: {e}")
        return False

def load_tweets_data():
    """Load all tweets data from JSON file"""
    try:
        if os.path.exists(TWEETS_DATA_FILE):
            with open(TWEETS_DATA_FILE, 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        st.error(f"Error loading tweets data: {e}")
        return {}

def save_tweets_data(tweets_data):
    """Save all tweets data to JSON file"""
    try:
        with open(TWEETS_DATA_FILE, 'w') as f:
            json.dump(tweets_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving tweets data: {e}")
        return False

def backup_tweet_to_monthly_json(ambassador_name, tweet_url, tweet_data):
    """Backup tweet data to monthly JSON file"""
    try:
        # Create backup directory if it doesn't exist
        Path(BACKUP_DIR).mkdir(exist_ok=True)
        
        # Get current month/year for filename
        current_month = datetime.now().strftime("%B_%Y").lower()  # e.g., "june_2025"
        backup_file = f"{BACKUP_DIR}/{current_month}.json"
        
        # Load existing data or create new
        if os.path.exists(backup_file):
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
        else:
            backup_data = {}
        
        # Add new tweet data
        if ambassador_name not in backup_data:
            backup_data[ambassador_name] = []
        
        backup_entry = {
            "tweet_url": tweet_url,
            "submitted_date": datetime.now().isoformat(),
            "tweet_id": tweet_data.get('tweet_id', ''),
            "impressions": tweet_data.get('impressions', 0),
            "likes": tweet_data.get('likes', 0),
            "retweets": tweet_data.get('retweets', 0),
            "replies": tweet_data.get('replies', 0)
        }
        
        backup_data[ambassador_name].append(backup_entry)
        
        # Save backup
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error backing up tweet: {e}")
        return False

def extract_tweet_id(url):
    """Extract tweet ID from Twitter/X URL"""
    patterns = [
        r'twitter\.com/\w+/status/(\d+)',
        r'x\.com/\w+/status/(\d+)',
        r'/status/(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def validate_tweet_url(url):
    """Basic validation for tweet URL format"""
    tweet_id = extract_tweet_id(url)
    if not tweet_id:
        return False, "Invalid tweet URL format"
    
    # Check if URL is accessible (basic check)
    try:
        parsed = urlparse(url)
        if parsed.netloc not in ['twitter.com', 'x.com', 'www.twitter.com', 'www.x.com']:
            return False, "URL must be from twitter.com or x.com"
        return True, tweet_id
    except:
        return False, "Invalid URL format"

def add_tweet(ambassador_name, tweet_url, impressions=0, likes=0, retweets=0, replies=0):
    """Add tweet to JSON data and backup"""
    
    is_valid, tweet_id_or_error = validate_tweet_url(tweet_url)
    if not is_valid:
        return False, tweet_id_or_error
    
    tweet_id = tweet_id_or_error
    
    # Load existing tweets data
    tweets_data = load_tweets_data()
    
    # Check if tweet already exists
    for ambassador, tweets in tweets_data.items():
        for tweet in tweets:
            if tweet.get('tweet_id') == tweet_id:
                return False, "Tweet already exists in database"
    
    # Add new tweet
    if ambassador_name not in tweets_data:
        tweets_data[ambassador_name] = []
    
    new_tweet = {
        "tweet_url": tweet_url,
        "tweet_id": tweet_id,
        "impressions": impressions,
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "submitted_date": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "final_update": False  # Will be set to True after 3-day update
    }
    
    tweets_data[ambassador_name].append(new_tweet)
    
    # Save to main data file
    if save_tweets_data(tweets_data):
        # Backup to monthly JSON
        backup_tweet_to_monthly_json(ambassador_name, tweet_url, new_tweet)
        sync_tweet_to_sheet(new_tweet, ambassador_name)

        return True, "Tweet added successfully"
    else:
        return False, "Failed to save tweet data"

def get_ambassador_stats():
    """Get comprehensive stats for all ambassadors from JSON data"""
    tweets_data = load_tweets_data()
    
    stats = []
    for ambassador_name, tweets in tweets_data.items():
        if tweets:  # Only include ambassadors with tweets
            total_tweets = len(tweets)
            total_impressions = sum(tweet.get('impressions', 0) for tweet in tweets)
            total_likes = sum(tweet.get('likes', 0) for tweet in tweets)
            total_retweets = sum(tweet.get('retweets', 0) for tweet in tweets)
            total_replies = sum(tweet.get('replies', 0) for tweet in tweets)
            avg_impressions = total_impressions / total_tweets if total_tweets > 0 else 0
            
            # Get last activity (most recent tweet submission)
            last_activity = max(tweet.get('submitted_date', '') for tweet in tweets)
            
            # Get date of first tweet posted
            first_tweet_date = min(tweet.get('submitted_date', '') for tweet in tweets)
            
            # Format dates for display
            try:
                last_activity_formatted = datetime.fromisoformat(last_activity).strftime('%b %d, %Y at %H:%M')
                first_tweet_formatted = datetime.fromisoformat(first_tweet_date).strftime('%b %d, %Y')
            except:
                last_activity_formatted = "Unknown"
                first_tweet_formatted = "Unknown"
            
            stats.append({
                'name': ambassador_name,
                'total_tweets': total_tweets,
                'total_impressions': total_impressions,
                'total_likes': total_likes,
                'total_retweets': total_retweets,
                'total_replies': total_replies,
                'avg_impressions': avg_impressions,
                'last_activity': last_activity_formatted,
                'first_tweet_date': first_tweet_formatted
            })
    
    # Sort by total impressions (descending)
    stats.sort(key=lambda x: x['total_impressions'], reverse=True)
    
    return pd.DataFrame(stats) if stats else pd.DataFrame()

def get_daily_impressions():
    """Get daily impression totals for charting from JSON data"""
    tweets_data = load_tweets_data()
    
    daily_data = {}
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    for ambassador_name, tweets in tweets_data.items():
        for tweet in tweets:
            submitted_date = datetime.fromisoformat(tweet.get('submitted_date', ''))
            if submitted_date >= thirty_days_ago:
                date_str = submitted_date.strftime('%Y-%m-%d')
                if date_str not in daily_data:
                    daily_data[date_str] = {
                        'date': date_str,
                        'daily_impressions': 0,
                        'tweets_submitted': 0
                    }
                daily_data[date_str]['daily_impressions'] += tweet.get('impressions', 0)
                daily_data[date_str]['tweets_submitted'] += 1
    
    # Convert to DataFrame and sort by date
    if daily_data:
        df = pd.DataFrame(list(daily_data.values()))
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        return df
    else:
        return pd.DataFrame()

def update_tweet_metrics(tweet_id, impressions, likes=None, retweets=None, replies=None):
    """Update tweet metrics in JSON data"""
    tweets_data = load_tweets_data()
    
    # Find and update the tweet
    for ambassador_name, tweets in tweets_data.items():
        for tweet in tweets:
            if tweet.get('tweet_id') == tweet_id:
                tweet['impressions'] = impressions
                if likes is not None:
                    tweet['likes'] = likes
                if retweets is not None:
                    tweet['retweets'] = retweets
                if replies is not None:
                    tweet['replies'] = replies
                tweet['last_updated'] = datetime.now().isoformat()
                
                # Save updated data
                save_tweets_data(tweets_data)
                return True
    return False

# Sidebar navigation
# Center the logo using columns
col1, col2, col3 = st.sidebar.columns([1, 2, 1])
with col2:
    st.image("img/nolus.png", width=120)  # Adjust width as needed

# Center the title
st.sidebar.markdown("<h1 style='text-align: center;'>Nolans Hub</h1>", unsafe_allow_html=True)

page = st.sidebar.selectbox(
    " ",
    ["➕ Submit Tweet", "📊 Leaderboard", "📈 Analytics", "⚙️ API Settings"]
)

# Main content based on selected page
if page == "📊 Leaderboard":
    st.title("📊 Ambassador Leaderboard")
    
    # Get stats
    stats_df = get_ambassador_stats()
    
    if len(stats_df) == 0:
        st.warning("No tweets submitted yet. Go to 'Submit Tweet' to add some!")
    else:
        # Top metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_impressions = stats_df['total_impressions'].sum()
            st.metric("Total Impressions", f"{total_impressions:,}")
        
        with col2:
            total_tweets = stats_df['total_tweets'].sum()
            st.metric("Total Tweets", f"{total_tweets:,}")
        
        with col3:
            active_ambassadors = len(stats_df)
            st.metric("Active Ambassadors", active_ambassadors)
        
        with col4:
            avg_impressions = stats_df['avg_impressions'].mean()
            st.metric("Avg Impressions/Tweet", f"{avg_impressions:.0f}")
        
        st.divider()
                
        # Leaderboard
        st.subheader("🏆 Leaderboard")
        
        # Format the dataframe for display
        display_df = stats_df.copy()
        display_df['total_impressions'] = display_df['total_impressions'].apply(lambda x: f"{x:,}")
        display_df['total_likes'] = display_df['total_likes'].apply(lambda x: f"{x:,}")
        display_df['total_replies'] = display_df['total_replies'].apply(lambda x: f"{x:,}")
        
        # Rename columns for display
        display_df = display_df.rename(columns={
            'name': 'Ambassador',
            'total_tweets': 'Tweets',
            'total_impressions': 'Total Impressions',
            'total_likes': 'Total Likes',
            'total_replies': 'Total Replies'
        })
        
        # Select columns to show
        columns_to_show = ['Ambassador', 'Tweets', 'Total Impressions', 'Total Likes', 'Total Replies']
        st.dataframe(
            display_df[columns_to_show],
            use_container_width=True,
            hide_index=True
        )

elif page == "➕ Submit Tweet":
    st.title("➕ Submit New Tweet")
    
    # Get ambassadors from JSON
    ambassadors_list = load_ambassadors_from_json()
    
    if len(ambassadors_list) == 0:
        st.error("No ambassadors found. Please check the ambassadors.json file.")
    else:
        with st.form("tweet_submission"):
            # Ambassador selection from dropdown
            selected_ambassador = st.selectbox("Select Ambassador", ambassadors_list)
            
            # Tweet URL
            tweet_url = st.text_input(
                "Tweet URL",
                placeholder="https://twitter.com/username/status/1234567890",
                help="Paste the full URL of the tweet"
            )
            
            submitted = st.form_submit_button("Submit Tweet", type="primary")
            
            if submitted:
                if not tweet_url:
                    st.error("Please enter a tweet URL")
                else:
                    # Add tweet with default metrics (will be updated later)
                    success, message = add_tweet(selected_ambassador, tweet_url, 0, 0, 0, 0)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info(f"📝 Tweet will be updated with impressions after 3 days")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()  # Refresh the page
                    else:
                        st.error(message)

elif page == "📈 Analytics":
    st.title("📈 Analytics Dashboard")
    
    # Daily impressions chart
    daily_df = get_daily_impressions()
    
    if len(daily_df) > 0:
        # Daily impressions line chart
        fig = px.line(
            daily_df, 
            x='date', 
            y='daily_impressions',
            title='Daily Impressions Trend (Last 30 Days)',
            labels={'daily_impressions': 'Impressions', 'date': 'Date'}
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # Ambassador performance comparison
        stats_df = get_ambassador_stats()
        if len(stats_df) > 0:
            fig2 = px.bar(
                stats_df.head(10), 
                x='name', 
                y='total_impressions',
                title='Top 10 Ambassadors by Total Impressions',
                labels={'total_impressions': 'Total Impressions', 'name': 'Ambassador'}
            )
            fig2.update_xaxes(tickangle=45)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Performance metrics
            col1, col2 = st.columns(2)
            
            with col1:
                # Top performer
                top_performer = stats_df.iloc[0]
                st.metric(
                    "🏆 Top Performer", 
                    top_performer['name'],
                    f"{top_performer['total_impressions']:,} impressions"
                )
            
            with col2:
                # Most active
                most_active = stats_df.loc[stats_df['total_tweets'].idxmax()]
                st.metric(
                    "🔥 Most Active", 
                    most_active['name'],
                    f"{most_active['total_tweets']} tweets"
                )
    
    else:
        st.info("No data available yet. Submit some tweets to see analytics!")

elif page == "⚙️ API Settings":
    st.title("⚙️ X API Configuration")
    
    # Smart API Management Dashboard
    show_smart_api_dashboard()
    
    st.divider()
    
    # Usage Information
    st.subheader("📊 API Usage Info")
    
    tweets_data = load_tweets_data()
    total_tweets = sum(len(tweets) for tweets in tweets_data.values())
    api_count = get_api_count()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Tweets", total_tweets)
    
    with col2:
        remaining = max(0, 100 - api_count)
        st.metric("API Calls Remaining", f"{remaining}/100")
    
    with col3:
        usage_percent = min(100, (api_count / 100) * 100)
        st.metric("API Usage", f"{usage_percent:.1f}%")
    
    st.divider()
    
    # Data Files Section
    st.subheader("📂 Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Main Data Files:**")
        
        # tweets_data.json
        if os.path.exists(TWEETS_DATA_FILE):
            with st.expander(f"📄 {TWEETS_DATA_FILE} ✅"):
                try:
                    tweets_data = load_tweets_data()
                    st.json(tweets_data)
                except Exception as e:
                    st.error(f"Error loading file: {e}")
        else:
            st.write(f"📄 {TWEETS_DATA_FILE} ❌")
            
        # ambassadors.json
        if os.path.exists(AMBASSADORS_FILE):
            with st.expander(f"📄 {AMBASSADORS_FILE} ✅"):
                try:
                    ambassadors_data = load_ambassadors_from_json()
                    st.json({"ambassadors": ambassadors_data})
                except Exception as e:
                    st.error(f"Error loading file: {e}")
        else:
            st.write(f"📄 {AMBASSADORS_FILE} ❌")
    
    with col2:
        st.write("**Monthly Backups:**")
        if os.path.exists(BACKUP_DIR):
            backup_files = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')]
            if backup_files:
                for file in sorted(backup_files):
                    backup_path = os.path.join(BACKUP_DIR, file)
                    with st.expander(f"📄 {file}"):
                        try:
                            with open(backup_path, 'r') as f:
                                backup_data = json.load(f)
                            st.json(backup_data)
                        except Exception as e:
                            st.error(f"Error loading {file}: {e}")
            else:
                st.info("No monthly backup files yet.")
        else:
            st.info("No backup directory found yet.")

# Clean sidebar - removed all the status indicators
st.sidebar.markdown("---")
st.sidebar.markdown(f"📊 Total Tweets: {len(load_tweets_data()) and sum(len(tweets) for tweets in load_tweets_data().values()) or 0}")

# Simple API counter in sidebar
api_count = get_api_count()
st.sidebar.markdown(f"📡 **API Calls: {api_count}/100**")

# Smart API status in sidebar
smart_stats = get_smart_update_stats()
if smart_stats['tweets_ready_for_update'] > 0:
    st.sidebar.markdown(f"🎯 **{smart_stats['tweets_ready_for_update']} tweets ready for 3-day update**")

# Show auto-updater status in sidebar
is_auto_running = is_sheet_updater_running()
if is_auto_running:
    st.sidebar.success("🟢 Auto-Updater: Running")
else:
    st.sidebar.warning("🟡 Auto-Updater: Stopped")