#!/usr/bin/env python3
"""
Google Scholar Citation Scraper using scholarly library
Scrapes citation data from Google Scholar profile and outputs JSON
"""

from scholarly import scholarly
import json
import time
import sys

class GoogleScholarScraper:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_profile_data(self):
        """Scrape the profile data using scholarly"""
        try:
            # Search for the author by scholar ID
            author = scholarly.search_author_id(self.user_id)
            
            # Fill in the author's details
            author_filled = scholarly.fill(author)
            
            # Extract profile info
            profile_data = self._extract_profile_info(author_filled)
            
            # Extract publications with citation data
            publications = self._extract_publications(author_filled)
            
            # Combine data
            result = {
                **profile_data,
                'publications': publications,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return result
            
        except Exception as e:
            print(f"Error scraping profile: {e}")
            return None

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
        if 'cites_per_year' in author:
            data['citations_per_year'] = author['cites_per_year']
        
        return data

    def _extract_publications(self, author):
        """Extract publications list with detailed information"""
        publications = []
        
        if 'publications' not in author:
            return publications
        
        for pub in author['publications']:
            try:
                # Fill publication details
                pub_filled = scholarly.fill(pub)
                
                pub_data = {
                    'title': pub_filled.get('bib', {}).get('title', ''),
                    'authors': pub_filled.get('bib', {}).get('author', ''),
                    'venue': pub_filled.get('bib', {}).get('venue', ''),
                    'year': pub_filled.get('bib', {}).get('pub_year'),
                    'citations': pub_filled.get('num_citations', 0),
                    'pub_url': pub_filled.get('pub_url', ''),
                    'eprint_url': pub_filled.get('eprint_url', ''),
                    'abstract': pub_filled.get('bib', {}).get('abstract', ''),
                }
                
                # Convert year to int if possible
                if pub_data['year']:
                    try:
                        pub_data['year'] = int(pub_data['year'])
                    except (ValueError, TypeError):
                        pass
                
                publications.append(pub_data)
                
            except Exception as e:
                print(f"Error processing publication: {e}")
                # Add basic info even if detailed scraping fails
                pub_data = {
                    'title': pub.get('bib', {}).get('title', ''),
                    'authors': pub.get('bib', {}).get('author', ''),
                    'year': pub.get('bib', {}).get('pub_year'),
                    'citations': pub.get('num_citations', 0),
                }
                publications.append(pub_data)
        
        # Sort by citation count (descending)
        publications.sort(key=lambda x: x.get('citations', 0), reverse=True)
        
        return publications

    def scrape_all(self):
        """Main scraping method"""
        print(f"Scraping Google Scholar profile: {self.user_id}")
        
        data = self.get_profile_data()
        if data:
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
    scraper = GoogleScholarScraper(user_id)
    
    data = scraper.scrape_all()
    
    if data:
        # Output to JSON file
        output_file = 'gs_data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {output_file}")
        
        # Also print summary
        print("\nSummary:")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Affiliation: {data.get('affiliation', 'N/A')}")
        print(f"Total Citations: {data.get('total_citations', 0)}")
        print(f"H-index: {data.get('h_index', 0)}")
        print(f"Publications: {len(data.get('publications', []))}")
    else:
        print("Failed to scrape data")
        sys.exit(1)

if __name__ == "__main__":
    main()