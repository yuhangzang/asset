#!/usr/bin/env python3
"""
Google Scholar Citation Scraper using official scholarly library
Scrapes citation data from Google Scholar profile and outputs JSON
"""

from scholarly import scholarly, ProxyGenerator
import json
import time
import sys
import signal
import os
from functools import wraps

def timeout(seconds=3600):
    """Timeout decorator to prevent hanging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
            
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        return wrapper
    return decorator

class GoogleScholarScholarlyScaper:
    def __init__(self, user_id):
        self.user_id = user_id
        
        # Detect if running in GitHub Actions
        self.is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
        print(f"Running in GitHub Actions: {self.is_github_actions}")
        
        # Setup scholarly with proxy if in CI
        self._setup_scholarly()
    
    def _setup_scholarly(self):
        """Setup scholarly with appropriate configuration"""
        try:
            # Test basic scholarly functionality first
            print("Testing scholarly library...")
            print(f"Scholarly version: {getattr(scholarly, '__version__', 'unknown')}")
            
            # Always try to set up proxy as recommended by scholarly docs
            print("Setting up scholarly with proxy (recommended by library)...")
            pg = ProxyGenerator()
            
            # Try free proxies first (especially important for CI)
            try:
                print("Attempting to configure free proxies...")
                success = pg.FreeProxies()
                print(f"Free proxy setup result: {success}")
                if success:
                    scholarly.use_proxy(pg)
                    print("Successfully configured free proxy")
                    return
            except Exception as e:
                print(f"Free proxy setup failed: {e}")
                import traceback
                traceback.print_exc()
            
            # If free proxies fail, continue without (not ideal but functional)
            print("Continuing without proxy - this may lead to rate limiting")
            
        except Exception as e:
            print(f"Error setting up scholarly: {e}")
            import traceback
            traceback.print_exc()
            print("Continuing without proxy...")

    @timeout(3600)  # 1 hour timeout
    def get_profile_data(self):
        """Scrape the profile data using scholarly library"""
        try:
            # For GitHub Actions, try using existing data if recent
            if self.is_github_actions and self._use_recent_data():
                return self._load_existing_data()
            
            print("Searching for author by ID...")
            # Search for the author by scholar ID using correct API
            try:
                # First try with filled=False for faster response
                print("Attempting search with filled=False...")
                author = scholarly.search_author_id(self.user_id, filled=False)
                print(f"Search result type: {type(author)}")
                print(f"Search result keys: {list(author.keys()) if isinstance(author, dict) else 'Not a dict'}")
                print(f"Author name: {author.get('name', 'Unknown') if isinstance(author, dict) else 'N/A'}")
                
                # If that worked but we want more data, we can try filled=True as backup
                if not author or not isinstance(author, dict):
                    print("First search didn't return expected result, trying filled=True...")
                    author = scholarly.search_author_id(self.user_id, filled=True)
                    print(f"Filled search result type: {type(author)}")
                elif isinstance(author, dict) and 'publications' not in author:
                    print("Basic search worked but no publications, trying filled=True with publication_limit...")
                    author = scholarly.search_author_id(self.user_id, filled=True, publication_limit=100)
                    print(f"Search with publications - keys: {list(author.keys()) if isinstance(author, dict) else 'Not a dict'}")
                    
            except Exception as e:
                print(f"Error searching for author: {e}")
                import traceback
                traceback.print_exc()
                print("Trying alternative search method...")
                return self._try_alternative_search()
            
            if not author:
                print(f"No author found with ID: {self.user_id}")
                print("Trying alternative search method...")
                return self._try_alternative_search()
            
            print(f"Found author: {author.get('name', 'Unknown')}")
            
            # Check if author is already filled
            is_filled = author.get('filled', False)
            print(f"Author filled status: {is_filled}")
            
            if not is_filled:
                print("Filling author details...")
                # Fill in the author's complete details with retry mechanism
                max_fill_attempts = 3
                author_filled = None
                
                for attempt in range(max_fill_attempts):
                    try:
                        if attempt > 0:
                            print(f"Fill attempt {attempt + 1}/{max_fill_attempts}")
                            time.sleep(10 * attempt)  # Exponential backoff
                        
                        author_filled = scholarly.fill(author)
                        print("Author details filled successfully")
                        break
                        
                    except Exception as e:
                        print(f"Error filling author details (attempt {attempt + 1}): {e}")
                        if attempt == max_fill_attempts - 1:
                            print("All fill attempts failed, using basic author data")
                            author_filled = author
            else:
                print("Author already filled, skipping fill step")
                author_filled = author
            
            print("Extracting profile information...")
            profile_data = self._extract_profile_info(author_filled)
            
            # Debug: print author structure
            print("=== DEBUG: Author Object Structure ===")
            if isinstance(author_filled, dict):
                for key, value in author_filled.items():
                    if key == 'publications':
                        print(f"{key}: [{len(value)} items]" if isinstance(value, list) else f"{key}: {type(value)}")
                    else:
                        print(f"{key}: {value}")
            print("=== END DEBUG ===")
            
            print("Extracting publications...")
            publications = self._extract_publications(author_filled, profile_data)
            
            # Combine data
            result = {
                **profile_data,
                'publications': publications,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'scraper_method': 'scholarly'
            }
            
            return result
            
        except TimeoutError as e:
            print(f"Scraping timed out: {e}")
            return self._fallback_data()
        except Exception as e:
            print(f"Error scraping profile: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_data()
    
    def _use_recent_data(self):
        """Check if we should use existing data instead of scraping"""
        if os.path.exists('gs_data.json'):
            try:
                with open('gs_data.json', 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    last_updated = existing_data.get('last_updated', '')
                    
                    if last_updated:
                        from datetime import datetime, timedelta
                        try:
                            last_date = datetime.strptime(last_updated, '%Y-%m-%d %H:%M:%S')
                            if datetime.now() - last_date < timedelta(days=7):
                                print("Found recent data (less than 7 days old), using existing")
                                return True
                        except ValueError:
                            pass
            except Exception as e:
                print(f"Error checking existing data: {e}")
        return False
    
    def _load_existing_data(self):
        """Load and update timestamp of existing data"""
        try:
            with open('gs_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
                data['note'] = 'Using recent existing data'
                return data
        except Exception as e:
            print(f"Error loading existing data: {e}")
            return None
    
    def _fallback_data(self):
        """Return fallback data if scraping fails"""
        fallback = {
            "name": "Yuhang Zang",
            "affiliation": "Shanghai AI Laboratory", 
            "interests": ["Vision Language Model", "Computer Vision", "Natural Language Processing"],
            "email_domain": "",
            "homepage": "",
            "total_citations": 0,
            "h_index": 0,
            "i10_index": 0,
            "citations_per_year": {},
            "publications": [],
            "last_updated": time.strftime('%Y-%m-%d %H:%M:%S'),
            "scraper_method": "scholarly",
            "note": "Fallback data due to scraping failure"
        }
        
        # Try to load existing data first
        if os.path.exists('gs_data.json'):
            try:
                with open('gs_data.json', 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    existing_data['note'] = 'Existing data due to scraping failure'
                    return existing_data
            except Exception:
                pass
        
        return fallback
    
    def _try_alternative_search(self):
        """Try alternative search methods when direct ID search fails"""
        try:
            print("Attempting alternative search by author name...")
            # Try searching by author name (we know this is Yuhang Zang)
            search_query = scholarly.search_author('Yuhang Zang')
            
            # Look for the first few results
            found_author = None
            for i, author in enumerate(search_query):
                if i >= 5:  # Only check first 5 results
                    break
                    
                print(f"Checking author {i+1}: {author.get('name', 'Unknown')} at {author.get('affiliation', 'Unknown')}")
                
                # Look for Shanghai AI Laboratory affiliation
                affiliation = author.get('affiliation', '').lower()
                if 'shanghai ai laboratory' in affiliation or 'shanghai ai lab' in affiliation:
                    print(f"Found matching author: {author.get('name')} at {author.get('affiliation')}")
                    found_author = author
                    break
                    
                # Also check if this might be the right person by name
                name = author.get('name', '').lower()
                if 'yuhang zang' in name:
                    print(f"Found author by name match: {author.get('name')} at {author.get('affiliation')}")
                    found_author = author
                    break
            
            if not found_author:
                print("No matching author found in alternative search")
                return self._fallback_data()
            
            # Try to fill the found author
            print("Filling alternative search result...")
            try:
                author_filled = scholarly.fill(found_author)
            except Exception as e:
                print(f"Error filling alternative author: {e}")
                author_filled = found_author
            
            # Extract data
            profile_data = self._extract_profile_info(author_filled)
            publications = self._extract_publications(author_filled, profile_data)
            
            # Combine data
            result = {
                **profile_data,
                'publications': publications,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'scraper_method': 'scholarly-alternative',
                'note': 'Found via alternative name search'
            }
            
            return result
            
        except Exception as e:
            print(f"Alternative search failed: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_data()
    
    def _extract_profile_info(self, author):
        """Extract basic profile information"""
        data = {}
        
        # Basic info
        data['name'] = author.get('name', '')
        data['affiliation'] = author.get('affiliation', '')
        data['interests'] = author.get('interests', [])
        data['email_domain'] = author.get('email_domain', '')
        data['homepage'] = author.get('homepage', '')
        
        # Citation stats
        data['total_citations'] = author.get('citedby', 0)
        data['h_index'] = author.get('hindex', 0)
        data['i10_index'] = author.get('i10index', 0)
        
        # Citation stats by year
        data['citations_per_year'] = author.get('cites_per_year', {})
        
        print(f"Profile: {data['name']} at {data['affiliation']}")
        print(f"Citations: {data['total_citations']}, H-index: {data['h_index']}, i10-index: {data['i10_index']}")
        
        return data
    
    def _extract_publications(self, author, profile_data):
        """Extract publications with detailed information"""
        publications = []
        
        print(f"Author object keys: {list(author.keys()) if isinstance(author, dict) else 'Not a dict'}")
        print(f"Author filled status: {author.get('filled', 'unknown')}")
        
        if 'publications' not in author:
            print("No 'publications' key found in author data")
            print("This might mean the author object is not filled or has no publications")
            
            # Try to fill the author if not already filled
            if not author.get('filled', False):
                print("Attempting to fill author to get publications...")
                try:
                    filled_author = scholarly.fill(author)
                    print(f"After fill - keys: {list(filled_author.keys())}")
                    if 'publications' in filled_author:
                        author = filled_author
                        print(f"Successfully filled author, now has {len(filled_author['publications'])} publications")
                    else:
                        print("Even after filling, no publications found")
                        return publications
                except Exception as e:
                    print(f"Error filling author: {e}")
                    return publications
            else:
                print("Author is marked as filled but still no publications")
                return publications
        
        author_pubs = author['publications']
        total_pubs = len(author_pubs)
        print(f"Found {total_pubs} publications")
        
        for i, pub in enumerate(author_pubs):
            try:
                print(f"Processing publication {i+1}/{total_pubs}: {pub.get('bib', {}).get('title', 'Unknown')}")
                
                # Debug: print publication keys to understand structure
                if i == 0:  # Only for first publication to avoid spam
                    print(f"DEBUG: First publication keys: {list(pub.keys())}")
                    print(f"DEBUG: author_pub_id: {pub.get('author_pub_id', 'NOT FOUND')}")
                    print(f"DEBUG: gsrank: {pub.get('gsrank', 'NOT FOUND')}")
                    print(f"DEBUG: container_type: {pub.get('container_type', 'NOT FOUND')}")
                    print(f"DEBUG: filled: {pub.get('filled', 'NOT FOUND')}")
                
                # Extract basic info first
                pub_data = {
                    'title': pub.get('bib', {}).get('title', ''),
                    'authors': pub.get('bib', {}).get('author', ''),
                    'venue': pub.get('bib', {}).get('venue', ''),
                    'year': pub.get('bib', {}).get('pub_year'),
                    'citations': pub.get('num_citations', 0),
                    'pub_url': pub.get('pub_url', ''),
                    'key': pub.get('author_pub_id', ''),  # The paper key like 'hW23VKIAAAAJ:u-x6o8ySG0sC'
                }
                
                # Try to get more details if available
                try:
                    if not pub_data['venue'] and 'bib' in pub:
                        # Try to extract venue from journal or conference
                        bib = pub['bib']
                        pub_data['venue'] = bib.get('journal', bib.get('conference', ''))
                    
                    # Convert year to int if possible
                    if pub_data['year']:
                        try:
                            pub_data['year'] = int(pub_data['year'])
                        except (ValueError, TypeError):
                            pass
                            
                except Exception as detail_error:
                    print(f"Error extracting details for publication {i+1}: {detail_error}")
                
                publications.append(pub_data)
                
                # Save intermediate results periodically
                if i % 10 == 0 and profile_data:
                    self._save_intermediate_result(profile_data, publications, i+1, total_pubs)
                
                # Add delay to avoid rate limiting
                delay = 2 if self.is_github_actions else 0.5
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error processing publication {i+1}: {e}")
                continue
        
        # Sort by citation count (descending)
        publications.sort(key=lambda x: x.get('citations', 0), reverse=True)
        print(f"Successfully extracted {len(publications)} publications")
        
        return publications
    
    def _save_intermediate_result(self, profile_data, publications, current, total):
        """Save intermediate results to avoid data loss"""
        try:
            sorted_pubs = sorted(publications, key=lambda x: x.get('citations', 0), reverse=True)
            
            result = {
                **profile_data,
                'publications': sorted_pubs,
                'scraping_progress': {
                    'current': current,
                    'total': total,
                    'percentage': round((current / total) * 100, 2)
                },
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
                'scraper_method': 'scholarly'
            }
            
            # Save to output file
            with open('gs_data.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Saved intermediate result: {current}/{total} publications ({result['scraping_progress']['percentage']}%)")
            
        except Exception as e:
            print(f"Error saving intermediate result: {e}")

    def scrape_all(self):
        """Main scraping method"""
        print(f"Scraping Google Scholar profile using scholarly library: {self.user_id}")
        
        data = self.get_profile_data()
        if data:
            # Remove scraping progress from final result
            if 'scraping_progress' in data:
                del data['scraping_progress']
            
            print(f"Successfully scraped {len(data.get('publications', []))} publications")
            return data
        else:
            print("Failed to scrape profile data")
            return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_scholar.py <user_id>")
        print("Example: python scrape_scholar.py hW23VKIAAAAJ")
        sys.exit(1)
    
    user_id = sys.argv[1]
    scraper = GoogleScholarScholarlyScaper(user_id)
    
    data = scraper.scrape_all()
    
    if data:
        # Output to JSON file
        output_file = 'gs_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Final data saved to {output_file}")
        
        # Print summary
        print("\nSummary:")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Affiliation: {data.get('affiliation', 'N/A')}")
        print(f"Total Citations: {data.get('total_citations', 0)}")
        print(f"H-index: {data.get('h_index', 0)}")
        print(f"i10-index: {data.get('i10_index', 0)}")
        print(f"Publications: {len(data.get('publications', []))}")
    else:
        print("Failed to scrape data")
        sys.exit(1)

if __name__ == "__main__":
    main()