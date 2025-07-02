#!/usr/bin/env python3
"""
X API Data Collector for Ambassador Dashboard
Fetches impression data for all tweets in tweets_data.json
Now supports smart 3-day collection mode
"""

import json
import os
import time
import tweepy
import sys
from datetime import datetime, timedelta

# File paths
CONFIG_FILE = "config.json"
TWEETS_DATA_FILE = "tweets_data.json"

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

def load_config():
    """Load X API configuration from environment variables or local file"""
    try:
        # Try environment variables first (for deployment)
        bearer_token = os.getenv('BEARER_TOKEN')
        if bearer_token:
            return {
                "x_api": {
                    "bearer_token": bearer_token,
                    "api_key": os.getenv('API_KEY', ''),
                    "api_secret": os.getenv('API_SECRET', ''),
                    "access_token": os.getenv('ACCESS_TOKEN', ''),
                    "access_token_secret": os.getenv('ACCESS_TOKEN_SECRET', '')
                }
            }
        
        # Fallback to local config file
        elif os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            print("❌ config.json not found and no environment variables set!")
            return {}
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return {}

def load_tweets_data():
    """Load all tweets data from JSON file"""
    try:
        if os.path.exists(TWEETS_DATA_FILE):
            with open(TWEETS_DATA_FILE, 'r') as f:
                return json.load(f)
        else:
            print("❌ tweets_data.json not found!")
            return {}
    except Exception as e:
        print(f"❌ Error loading tweets data: {e}")
        return {}

def save_tweets_data(tweets_data):
    """Save all tweets data to JSON file"""
    try:
        with open(TWEETS_DATA_FILE, 'w') as f:
            json.dump(tweets_data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving tweets data: {e}")
        return False

def init_x_api():
    """Initialize X API client"""
    config = load_config()
    
    try:
        bearer_token = config.get('x_api', {}).get('bearer_token', '')
        
        if bearer_token and bearer_token != "YOUR_BEARER_TOKEN_HERE":
            client = tweepy.Client(bearer_token=bearer_token)
            return client
        else:
            print("❌ Bearer token not configured in config.json")
            return None
    except Exception as e:
        print(f"❌ Error initializing X API: {e}")
        return None

def fetch_tweet_impressions(tweet_id, client):
    """Fetch only impressions from X API (minimal request)"""
    try:
        print(f"   📡 Making API call for tweet {tweet_id}")
        
        # Fetch tweet data with only public metrics (minimal fields)
        tweet = client.get_tweet(
            tweet_id,
            tweet_fields=['public_metrics']
        )
        
        # COUNT EVERY API CALL - REGARDLESS OF SUCCESS/FAILURE
        count = increment_api_count()
        print(f"   📊 API call #{count} logged")
        
        if tweet.data:
            metrics = tweet.data.public_metrics
            impressions = metrics.get('impression_count', 0)
            print(f"   ✅ Got {impressions} impressions")
            return impressions
        else:
            print(f"   ❌ No data returned")
            return None
            
    except tweepy.NotFound:
        print(f"⚠️ Tweet {tweet_id} not found (may be deleted)")
        # COUNT FAILED API CALLS TOO
        count = increment_api_count()
        print(f"   📊 Failed API call #{count} logged")
        return None
    except tweepy.Unauthorized:
        print(f"❌ Unauthorized access to tweet {tweet_id}")
        # COUNT FAILED API CALLS TOO
        count = increment_api_count()
        print(f"   📊 Failed API call #{count} logged")
        return None
    except tweepy.TooManyRequests:
        print(f"❌ Rate limit exceeded!")
        # COUNT FAILED API CALLS TOO
        count = increment_api_count()
        print(f"   📊 Failed API call #{count} logged")
        return None
    except Exception as e:
        print(f"❌ Error fetching tweet {tweet_id}: {e}")
        # COUNT FAILED API CALLS TOO
        count = increment_api_count()
        print(f"   📊 Failed API call #{count} logged")
        return None

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
                        'days_old': (datetime.now() - submitted_date).days,
                        'tweet_obj': tweet  # Reference to the actual tweet object
                    })
    
    # Sort by oldest first
    ready_for_update.sort(key=lambda x: x['submitted_date'])
    return ready_for_update

def update_smart_impressions():
    """Update impressions only for tweets that are 3+ days old and haven't been updated"""
    print("🧠 Smart API collection - only updating 3+ day old tweets...")
    
    # Get tweets ready for update
    ready_tweets = get_tweets_ready_for_update()
    
    if not ready_tweets:
        print("✅ No tweets need updating right now!")
        print("   All tweets are either:")
        print("   • Less than 3 days old (waiting for engagement to stabilize)")
        print("   • Already updated with final impressions")
        return True
    
    print(f"📊 Found {len(ready_tweets)} tweets ready for 3-day update:")
    for tweet in ready_tweets[:5]:  # Show first 5
        print(f"   • {tweet['ambassador']}: {tweet['days_old']} days old")
    
    if len(ready_tweets) > 5:
        print(f"   ... and {len(ready_tweets) - 5} more")
    
    # Initialize API client
    client = init_x_api()
    if not client:
        return False
    
    # Load full tweets data for updating
    tweets_data = load_tweets_data()
    
    updated_count = 0
    
    # Process each ready tweet
    for ready_tweet in ready_tweets:
        tweet_id = ready_tweet['tweet_id']
        ambassador = ready_tweet['ambassador']
        
        print(f"\n📝 Updating {ambassador}'s tweet ({ready_tweet['days_old']} days old)")
        
        # Find the actual tweet object to update
        for tweet in tweets_data[ambassador]:
            if tweet.get('tweet_id') == tweet_id:
                impressions = fetch_tweet_impressions(tweet_id, client)
                
                if impressions is not None:
                    old_impressions = tweet.get('impressions', 0)
                    tweet['impressions'] = impressions
                    tweet['last_updated'] = datetime.now().isoformat()
                    tweet['final_update'] = True  # Mark as final 3-day update
                    
                    print(f"   ✅ Final update: {old_impressions} → {impressions} impressions")
                    updated_count += 1
                else:
                    print(f"   ❌ Failed to fetch impressions")
                
                break
        
        # Small delay between requests
        time.sleep(1)
    
    # Save updated data
    if save_tweets_data(tweets_data):
        print(f"\n🎉 Smart collection complete!")
        print(f"✅ Updated {updated_count} tweets with final 3-day impressions")
        return True
    else:
        print(f"\n❌ Failed to save updated data")
        return False

def update_all_impressions():
    """Update impressions for all tweets using X API (legacy mode)"""
    print("🚀 Starting X API data collection (ALL TWEETS)...")
    
    # Initialize API client
    client = init_x_api()
    if not client:
        print("❌ Cannot initialize X API client")
        return False
    
    # Load tweets data
    tweets_data = load_tweets_data()
    if not tweets_data:
        print("❌ No tweets data found")
        return False
    
    # Count total tweets
    total_tweets = sum(len(tweets) for tweets in tweets_data.values())
    print(f"📊 Found {total_tweets} tweets to update")
    
    if total_tweets == 0:
        print("❌ No tweets found to update")
        return False
    
    if total_tweets > 100:
        print(f"⚠️ Warning: {total_tweets} tweets exceed X API free tier limit (100/month)")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    
    updated_count = 0
    error_count = 0
    tweet_counter = 0
    
    # Process each ambassador's tweets
    for ambassador_name, tweets in tweets_data.items():
        print(f"📝 Processing {ambassador_name}...")
        
        for tweet in tweets:
            tweet_counter += 1
            tweet_id = tweet.get('tweet_id')
            
            if tweet_id:
                print(f"   Fetching tweet {tweet_counter}/{total_tweets}: {tweet_id}")
                
                impressions = fetch_tweet_impressions(tweet_id, client)
                
                if impressions is not None:
                    # Update impressions
                    old_impressions = tweet.get('impressions', 0)
                    tweet['impressions'] = impressions
                    tweet['last_updated'] = datetime.now().isoformat()
                    
                    print(f"   ✅ Updated: {old_impressions} → {impressions} impressions")
                    updated_count += 1
                else:
                    print(f"   ❌ Failed to fetch impressions")
                    error_count += 1
                
                # Rate limiting - delay between requests
                time.sleep(1)  # 1 second delay to be safe
            else:
                print(f"   ⚠️ No tweet_id found for tweet")
                error_count += 1
    
    # Save updated data
    if save_tweets_data(tweets_data):
        print(f"\n🎉 Collection complete!")
        print(f"✅ Successfully updated: {updated_count} tweets")
        print(f"❌ Errors: {error_count} tweets")
        print(f"📁 Data saved to {TWEETS_DATA_FILE}")
        return True
    else:
        print(f"\n❌ Failed to save updated data")
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("🐦 X API Data Collector for Ambassador Dashboard")
    print("=" * 50)
    
    # Check for smart mode flag
    smart_mode = "--smart" in sys.argv
    
    if smart_mode:
        print("🧠 Running in SMART mode (3-day strategy)")
    else:
        print("🔄 Running in LEGACY mode (all tweets)")
    
    # Check if files exist
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ {CONFIG_FILE} not found!")
        print("   Please configure your X API credentials first.")
        return
    
    if not os.path.exists(TWEETS_DATA_FILE):
        print(f"❌ {TWEETS_DATA_FILE} not found!")
        print("   Please submit some tweets in the dashboard first.")
        return
    
    # Run the appropriate update mode
    if smart_mode:
        success = update_smart_impressions()
    else:
        success = update_all_impressions()
    
    if success:
        print("\n✅ All done! Check your dashboard to see updated impressions.")
    else:
        print("\n❌ Data collection failed. Check the errors above.")

if __name__ == "__main__":
    main()