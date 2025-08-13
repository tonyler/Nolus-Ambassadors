import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import streamlit as st
import praw

load_dotenv()

class UpdateService:
    def __init__(self):
        # Try Streamlit secrets first, then environment variables
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_ANON_KEY"]
            reddit_client_id = st.secrets.get("REDDIT_CLIENT_ID")
            reddit_client_secret = st.secrets.get("REDDIT_CLIENT_SECRET") 
            reddit_user_agent = st.secrets.get("REDDIT_USER_AGENT")
        except:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")
            reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
            reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            reddit_user_agent = os.getenv("REDDIT_USER_AGENT")
        
        self.supabase = create_client(url, key)
        
        # Initialize Reddit API client
        try:
            self.reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent
            )
            print("☁️ Streamlit Cloud service initialized with Reddit API")
        except Exception as e:
            print(f"⚠️ Reddit API initialization failed: {e}")
            self.reddit = None
    
    def extract_tweet_id(self, tweet_url):
        try:
            if "/status/" in tweet_url:
                return tweet_url.split("/status/")[-1].split("?")[0]
            return None
        except:
            return None
    
    def extract_reddit_id(self, reddit_url):
        try:
            if "/comments/" in reddit_url:
                return reddit_url.split("/comments/")[-1].split("/")[0]
            return None
        except:
            return None
    
    def add_new_tweet(self, ambassador, tweet_url):
        try:
            tweet_id = self.extract_tweet_id(tweet_url)
            if not tweet_id:
                return False, "Invalid tweet URL format"
            
            existing = self.supabase.table("ambassadors").select("id").eq("Tweet_URL", tweet_url).execute()
            if existing.data:
                return False, "Tweet URL already exists"
            
            tweet_data = {
                "Ambassador": ambassador,
                "Tweet_ID": tweet_id,
                "Tweet_URL": tweet_url,
                "Submitted_Date": datetime.now().isoformat(),
                "Last_Updated": datetime.now().isoformat(),
                "Final_Update": False,
                "Impressions": 0,
                "Likes": 0,
                "Retweets": 0,
                "Replies": 0
            }
            
            result = self.supabase.table("ambassadors").insert(tweet_data).execute()
            return True, f"Tweet added for {ambassador}" if result.data else (False, "Failed to insert")
                
        except Exception as e:
            error_msg = str(e)
            if "duplicate key value violates unique constraint" in error_msg and "Tweet_ID" in error_msg:
                return False, "Link has been added already"
            return False, f"Database error: {error_msg}"
    
    def add_new_reddit_post(self, ambassador, reddit_url):
        try:
            # Extract Reddit post ID from URL
            post_id = self.extract_reddit_id(reddit_url)
            if not post_id:
                return False, "Invalid Reddit URL format"
            
            existing = self.supabase.table("reddit").select("id").eq("url", reddit_url).execute()
            if existing.data:
                return False, "Reddit URL already exists"
            
            reddit_data = {
                "poster": ambassador,
                "url": reddit_url,
                "submitted_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("reddit").insert(reddit_data).execute()
            return True, f"Reddit post added for {ambassador}" if result.data else (False, "Failed to insert")
                
        except Exception as e:
            error_msg = str(e)
            if "duplicate key value violates unique constraint" in error_msg:
                return False, "Link has been added already"
            return False, f"Database error: {error_msg}"
    
    def get_leaderboard(self, year=None, month=None):
        try:
            query = self.supabase.table("ambassadors").select("*").not_.is_("date_posted", "null")
            
            # Filter by month/year if provided
            if year and month:
                # Get start and end of month
                start_date = datetime(year, month, 1).date()
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
                
                query = query.gte("date_posted", start_date.isoformat()).lte("date_posted", end_date.isoformat())
            
            result = query.execute()
            if not result.data:
                return []
            
            ambassador_stats = {}
            total_impressions_all = 0  # Track total from ALL posts for top metric
            
            for tweet in result.data:
                name = tweet["Ambassador"]
                if name not in ambassador_stats:
                    ambassador_stats[name] = {
                        "name": name,
                        "tweets": 0,
                        "total_impressions": 0,
                        "total_likes": 0,
                        "total_replies": 0,
                        "total_retweets": 0
                    }
                
                ambassador_stats[name]["tweets"] += 1
                ambassador_stats[name]["total_impressions"] += tweet["Impressions"]
                ambassador_stats[name]["total_likes"] += tweet["Likes"]
                ambassador_stats[name]["total_replies"] += tweet["Replies"]
                ambassador_stats[name]["total_retweets"] += tweet["Retweets"]
                
                # Always add to total for top metric (regardless of 500+ filter)
                total_impressions_all += tweet["Impressions"]
            
            leaderboard = list(ambassador_stats.values())
            leaderboard.sort(key=lambda x: x["total_impressions"], reverse=True)
            
            # Add the unfiltered total to the return data
            return leaderboard, total_impressions_all
        except:
            return [], 0
    
    def get_reddit_leaderboard(self, year=None, month=None):
        try:
            query = self.supabase.table("reddit").select("*").not_.is_("Score", "null")
            
            # Filter by month/year if provided
            if year and month:
                # Get start and end of month
                start_date = datetime(year, month, 1).date()
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
                
                query = query.gte("submitted_at", start_date.isoformat()).lte("submitted_at", end_date.isoformat())
            
            result = query.execute()
            print(f"🔍 Reddit query result: {result.data}")  # Debug print
            if not result.data:
                return []
            
            ambassador_stats = {}
            for post in result.data:
                name = post["poster"]  # Use correct column name
                print(f"🔍 Processing post: {name} - Score: {post.get('Score', 0)}")  # Debug print
                if name not in ambassador_stats:
                    ambassador_stats[name] = {
                        "name": name,
                        "posts": 0,
                        "total_score": 0,
                        "total_comments": 0,
                        "total_views": 0
                    }
                
                ambassador_stats[name]["posts"] += 1
                ambassador_stats[name]["total_score"] += post.get("Score", 0)
                ambassador_stats[name]["total_comments"] += post.get("Comments", 0) if post.get("Comments") else 0
                ambassador_stats[name]["total_views"] += post.get("Views", 0) if post.get("Views") else 0
            
            leaderboard = list(ambassador_stats.values())
            leaderboard.sort(key=lambda x: x["total_score"], reverse=True)
            print(f"🔍 Final leaderboard: {leaderboard}")  # Debug print
            return leaderboard
        except Exception as e:
            print(f"❌ Reddit leaderboard error: {e}")  # Debug print
            return []
    
    def get_update_stats(self):
        try:
            all_tweets = self.supabase.table("ambassadors").select("*").execute()
            # Changed from Final_Update = True to date_posted is not NULL
            updated_tweets = self.supabase.table("ambassadors").select("*").not_.is_("date_posted", "null").execute()
            cutoff_date = datetime.now() - timedelta(days=3)
            cutoff_iso = cutoff_date.isoformat()
            # Changed from Final_Update = False to date_posted is NULL
            ready_tweets = self.supabase.table("ambassadors").select("*").is_("date_posted", "null").lt("Submitted_Date", cutoff_iso).execute()
            
            total = len(all_tweets.data) if all_tweets.data else 0
            updated = len(updated_tweets.data) if updated_tweets.data else 0
            ready = len(ready_tweets.data) if ready_tweets.data else 0
            
            return {
                "total_tweets": total,
                "tweets_updated": updated,
                "tweets_ready_for_update": ready,
                "tweets_under_3_days": max(0, total - updated - ready)
            }
        except:
            return {"total_tweets": 0, "tweets_updated": 0, "tweets_ready_for_update": 0, "tweets_under_3_days": 0}
    
    def normalize_x_url(self, url):
        """Convert various X/Twitter URL formats to standard x.com format"""
        # Replace various X/Twitter domains with x.com
        url = url.replace("twitter.com", "x.com")
        url = url.replace("fixupx.com", "x.com")
        url = url.replace("fxtwitter.com", "x.com")
        return url
    
    def is_x_url(self, url):
        """Check if URL is from X/Twitter (any supported format)"""
        url_lower = url.lower()
        return any(domain in url_lower for domain in ["x.com", "twitter.com", "fixupx.com", "fxtwitter.com"])
    
    def add_content(self, ambassador, content_url):
        """Unified method to add content - detects platform from URL"""
        try:
            # Detect platform from URL
            if self.is_x_url(content_url):
                # Normalize X URL to x.com format
                normalized_url = self.normalize_x_url(content_url)
                print(f"🐦 X content added for {ambassador}")
                return self.add_new_tweet(ambassador, normalized_url)
            elif "reddit.com" in content_url.lower():
                print(f"📱 Reddit content added for {ambassador}")
                return self.add_new_reddit_post(ambassador, content_url)
            else:
                return False, "Unsupported platform. Please use X (Twitter) or Reddit URLs."
        except Exception as e:
            return False, f"Error processing URL: {str(e)}"
    
    def get_ready_tweets(self):
        try:
            cutoff_date = datetime.now() - timedelta(days=3)
            cutoff_iso = cutoff_date.isoformat()
            # Changed from Final_Update = False to date_posted is NULL
            result = self.supabase.table("ambassadors").select("*").is_("date_posted", "null").lt("Submitted_Date", cutoff_iso).execute()
            ready_tweets = result.data if result.data else []
            
            for tweet in ready_tweets:
                submitted = datetime.fromisoformat(tweet["Submitted_Date"].replace("Z", "+00:00").replace("+00:00", ""))
                age_days = (datetime.now() - submitted).days
                tweet["days_old"] = age_days
            
            return ready_tweets
        except:
            return []
    
    def calculate_daily_impressions(self, force_update=False):
        """Calculate and store daily impression gains"""
        try:
            today = datetime.now().date()
            
            # Get total impressions from all tweets today
            all_tweets = self.supabase.table("ambassadors").select("Impressions").execute()
            current_total = sum([tweet.get("Impressions", 0) for tweet in all_tweets.data]) if all_tweets.data else 0
            
            # Check if today's record already exists
            existing = self.supabase.table("daily_impressions").select("*").eq("date", today.isoformat()).execute()
            
            if existing.data:
                # Update existing record - calculate gain from yesterday's total
                record_id = existing.data[0]["id"]
                
                # Get yesterday's total to calculate proper gain
                yesterday = today - timedelta(days=1)
                yesterday_record = self.supabase.table("daily_impressions").select("total_impressions").eq("date", yesterday.isoformat()).execute()
                
                if yesterday_record.data:
                    yesterday_total = yesterday_record.data[0]["total_impressions"]
                    impressions_gained = current_total - yesterday_total
                    print(f"🔍 DEBUG: Today: {current_total}, Yesterday: {yesterday_total}, Gained: {impressions_gained}")
                else:
                    # If no yesterday record, assume yesterday was 0
                    impressions_gained = current_total
                    print(f"🔍 DEBUG: No yesterday record - Today: {current_total}, Gained: {impressions_gained}")
                
                self.supabase.table("daily_impressions").update({
                    "total_impressions": current_total,
                    "impressions_gained": max(0, impressions_gained)  # Ensure non-negative
                }).eq("id", record_id).execute()
                
                print(f"📊 Updated daily impressions: +{impressions_gained} (Total: {current_total})")
                return True, f"Daily impressions updated: +{impressions_gained}"
            else:
                # Get yesterday's total to calculate gain
                yesterday = today - timedelta(days=1)
                yesterday_record = self.supabase.table("daily_impressions").select("total_impressions").eq("date", yesterday.isoformat()).execute()
                
                if yesterday_record.data:
                    # Normal case: calculate gain from yesterday
                    yesterday_total = yesterday_record.data[0]["total_impressions"]
                    impressions_gained = current_total - yesterday_total
                else:
                    # First run: set gained to 0 (baseline)
                    impressions_gained = 0
                    print("📊 First run detected - setting baseline with 0 gained impressions")
                
                # Insert new record
                self.supabase.table("daily_impressions").insert({
                    "date": today.isoformat(),
                    "total_impressions": current_total,
                    "impressions_gained": max(0, impressions_gained)  # Ensure non-negative
                }).execute()
                
                if yesterday_record.data:
                    print(f"📊 New daily impressions record: +{impressions_gained} (Total: {current_total})")
                    return True, f"Daily impressions recorded: +{impressions_gained}"
                else:
                    print(f"📊 Baseline set: {current_total} total impressions")
                    return True, f"Baseline established: {current_total} total impressions (0 gained today)"
                
        except Exception as e:
            print(f"❌ Error calculating daily impressions: {e}")
            return False, f"Error: {str(e)}"
    
    def get_daily_impressions_for_month(self, year=None, month=None):
        """Get daily impression gains for a specific month"""
        try:
            if not year:
                year = datetime.now().year
            if not month:
                month = datetime.now().month
                
            # Get start and end of month
            start_date = datetime(year, month, 1).date()
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day).date()
            
            result = self.supabase.table("daily_impressions").select("date, impressions_gained").gte("date", start_date.isoformat()).lte("date", end_date.isoformat()).order("date").execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching daily impressions: {e}")
            return []
    
    def reset_today_impressions(self):
        """Reset today's record to 0 gained impressions (useful for first run correction)"""
        try:
            today = datetime.now().date()
            
            # Get total impressions from all tweets
            all_tweets = self.supabase.table("ambassadors").select("Impressions").execute()
            current_total = sum([tweet.get("Impressions", 0) for tweet in all_tweets.data]) if all_tweets.data else 0
            
            # Update today's record to 0 gained
            result = self.supabase.table("daily_impressions").update({
                "total_impressions": current_total,
                "impressions_gained": 0
            }).eq("date", today.isoformat()).execute()
            
            if result.data:
                print(f"📊 Reset today's impressions to baseline: {current_total} total, 0 gained")
                return True, f"Today reset to baseline: {current_total} total impressions"
            else:
                return False, "No record found for today"
                
        except Exception as e:
            print(f"❌ Error resetting today's impressions: {e}")
            return False, f"Error: {str(e)}"
    
    def auto_calculate_daily_impressions(self):
        """Auto-calculate daily impressions only if needed (smart logic)"""
        try:
            today = datetime.now().date()
            
            # Check if today's record already exists
            existing = self.supabase.table("daily_impressions").select("*").eq("date", today.isoformat()).execute()
            
            if existing.data:
                # Record exists - check if it needs updating (only update once per hour to avoid spam)
                existing_record = existing.data[0]
                created_at = datetime.fromisoformat(existing_record['created_at'].replace('Z', '+00:00'))
                hours_since_creation = (datetime.now(created_at.tzinfo) - created_at).total_seconds() / 3600
                
                if hours_since_creation >= 1:  # Update if more than 1 hour old
                    return self.calculate_daily_impressions(force_update=True)
                else:
                    return True, "Daily impressions already calculated recently"
            else:
                # No record for today - create one
                return self.calculate_daily_impressions()
                
        except Exception as e:
            print(f"❌ Error in auto-calculation: {e}")
            return False, f"Auto-calculation error: {str(e)}"
    
    def get_total_leaderboard(self, year=None, month=None):
        """Get combined views leaderboard from both X and Reddit platforms - only counts posts with >500 impressions/views"""
        try:
            # Get X data directly from database with 500+ impression filter
            query = self.supabase.table("ambassadors").select("*").not_.is_("date_posted", "null").gt("Impressions", 500)
            
            # Filter by month/year if provided
            if year and month:
                # Get start and end of month
                start_date = datetime(year, month, 1).date()
                from calendar import monthrange
                last_day = monthrange(year, month)[1]
                end_date = datetime(year, month, last_day).date()
                
                query = query.gte("date_posted", start_date.isoformat()).lte("date_posted", end_date.isoformat())
            
            x_result = query.execute()
            
            # Get Reddit data directly from database (no filtering - include all Reddit posts)
            reddit_query = self.supabase.table("reddit").select("*").not_.is_("Score", "null")
            
            # Filter by month/year if provided
            if year and month:
                reddit_query = reddit_query.gte("submitted_at", start_date.isoformat()).lte("submitted_at", end_date.isoformat())
            
            reddit_result = reddit_query.execute()
            
            # Combine views by ambassador name
            combined_stats = {}
            
            # Process X data (impressions = views) - only posts with >500 impressions
            if x_result.data:
                for tweet in x_result.data:
                    name = tweet["Ambassador"]
                    if name not in combined_stats:
                        combined_stats[name] = {
                            "name": name,
                            "x_views": 0,
                            "reddit_views": 0,
                            "total_views": 0
                        }
                    combined_stats[name]["x_views"] += tweet["Impressions"]
                    combined_stats[name]["total_views"] += tweet["Impressions"]
            
            # Process Reddit data - include all Reddit posts (use actual Views field)
            if reddit_result.data:
                for post in reddit_result.data:
                    name = post["poster"]
                    views = post.get("Views", 0) if post.get("Views") else 0
                    if name not in combined_stats:
                        combined_stats[name] = {
                            "name": name,
                            "x_views": 0,
                            "reddit_views": views,
                            "total_views": views
                        }
                    else:
                        combined_stats[name]["reddit_views"] += views
                        combined_stats[name]["total_views"] += views
            
            # Convert to list and sort by total views
            total_leaderboard = list(combined_stats.values())
            
            # Separate Tony from other ambassadors
            tony_entry = None
            other_ambassadors = []
            
            for ambassador in total_leaderboard:
                if ambassador["name"].lower() == "tony":
                    tony_entry = ambassador
                else:
                    other_ambassadors.append(ambassador)
            
            # Sort other ambassadors by total views (descending)
            other_ambassadors.sort(key=lambda x: x["total_views"], reverse=True)
            
            # Create final leaderboard with Tony at the bottom
            final_leaderboard = other_ambassadors
            if tony_entry:
                final_leaderboard.append(tony_entry)
            
            return final_leaderboard
        except Exception as e:
            print(f"❌ Total leaderboard error: {e}")
            return []
    
    def get_available_months(self):
        """Get list of available months with data from both X and Reddit platforms"""
        try:
            months_set = set()
            
            # Get months from X data
            x_result = self.supabase.table("ambassadors").select("date_posted").not_.is_("date_posted", "null").execute()
            if x_result.data:
                for record in x_result.data:
                    if record["date_posted"]:
                        date_obj = datetime.fromisoformat(record["date_posted"]).date()
                        # Filter out June 2025 and any future dates
                        if not (date_obj.year == 2025 and date_obj.month == 6):
                            months_set.add((date_obj.year, date_obj.month))
            
            # Get months from Reddit data
            reddit_result = self.supabase.table("reddit").select("submitted_at").not_.is_("Score", "null").execute()
            if reddit_result.data:
                for record in reddit_result.data:
                    if record["submitted_at"]:
                        date_obj = datetime.fromisoformat(record["submitted_at"]).date()
                        # Filter out June 2025 and any future dates
                        if not (date_obj.year == 2025 and date_obj.month == 6):
                            months_set.add((date_obj.year, date_obj.month))
            
            # Convert to sorted list of tuples (year, month), filter out future dates
            current_date = datetime.now().date()
            available_months = sorted([
                (year, month) for year, month in months_set 
                if datetime(year, month, 1).date() <= current_date
            ], reverse=True)
            return available_months
        except Exception as e:
            print(f"❌ Error getting available months: {e}")
            return []
    
    def update_reddit_stats(self):
        """Update Reddit stats by fetching fresh data from Reddit API - current month only"""
        try:
            if not self.reddit:
                return False, "Reddit API not initialized - check credentials"
            
            # Get current month date range
            current_date = datetime.now()
            start_date = datetime(current_date.year, current_date.month, 1).date()
            from calendar import monthrange
            last_day = monthrange(current_date.year, current_date.month)[1]
            end_date = datetime(current_date.year, current_date.month, last_day).date()
            
            # Get only current month's Reddit posts from database
            reddit_posts = self.supabase.table("reddit").select("*").gte("submitted_at", start_date.isoformat()).lte("submitted_at", end_date.isoformat()).execute()
            
            if not reddit_posts.data:
                current_month_name = current_date.strftime("%B %Y")
                return True, f"No Reddit posts found for {current_month_name}"
            
            updated_count = 0
            failed_count = 0
            
            for post in reddit_posts.data:
                try:
                    post_id = self.extract_reddit_id(post.get('url', ''))
                    if not post_id:
                        print(f"⚠️ Could not extract post ID from URL: {post.get('url', 'No URL')}")
                        failed_count += 1
                        continue
                    
                    # Fetch post data from Reddit API
                    reddit_post = self.reddit.submission(id=post_id)
                    
                    # Get fresh stats
                    score = reddit_post.score
                    num_comments = reddit_post.num_comments
                    
                    # Reddit doesn't provide view count in API, so we'll keep existing value or set 0
                    existing_views = post.get('Views', 0)
                    
                    # Update database with fresh stats
                    update_data = {
                        'Score': score,
                        'Comments': num_comments,
                        'Views': existing_views  # Keep existing views as Reddit API doesn't provide this
                    }
                    
                    self.supabase.table("reddit").update(update_data).eq("id", post["id"]).execute()
                    
                    print(f"✅ Updated {post.get('poster', 'Unknown')}'s post: Score={score}, Comments={num_comments}")
                    updated_count += 1
                    
                except Exception as post_error:
                    print(f"❌ Failed to update post {post_id}: {str(post_error)}")
                    failed_count += 1
                    continue
            
            current_month_name = current_date.strftime("%B %Y")
            print(f"📊 Reddit API refresh complete for {current_month_name}: {updated_count} updated, {failed_count} failed")
            
            if updated_count > 0:
                return True, f"Updated {updated_count} {current_month_name} Reddit posts with fresh API data"
            elif failed_count > 0:
                return False, f"Failed to update {failed_count} {current_month_name} posts - check post URLs and API access"
            else:
                return True, f"No {current_month_name} posts needed updating"
            
        except Exception as e:
            print(f"❌ Error updating Reddit stats: {e}")
            return False, f"Reddit API error: {str(e)}"
    
    def remove_june_2025_data(self):
        """Remove any erroneous June 2025 data from the database"""
        try:
            # Remove from X/Twitter data
            x_result = self.supabase.table("ambassadors").delete().gte("date_posted", "2025-06-01").lt("date_posted", "2025-07-01").execute()
            x_deleted = len(x_result.data) if x_result.data else 0
            
            # Remove from Reddit data  
            reddit_result = self.supabase.table("reddit").delete().gte("submitted_at", "2025-06-01").lt("submitted_at", "2025-07-01").execute()
            reddit_deleted = len(reddit_result.data) if reddit_result.data else 0
            
            # Remove from daily impressions data
            daily_result = self.supabase.table("daily_impressions").delete().gte("date", "2025-06-01").lt("date", "2025-07-01").execute()
            daily_deleted = len(daily_result.data) if daily_result.data else 0
            
            total_deleted = x_deleted + reddit_deleted + daily_deleted
            print(f"🗑️ Removed June 2025 data: {x_deleted} X posts, {reddit_deleted} Reddit posts, {daily_deleted} daily records")
            
            return True, f"Removed {total_deleted} June 2025 records"
        except Exception as e:
            print(f"❌ Error removing June 2025 data: {e}")
            return False, f"Error: {str(e)}"