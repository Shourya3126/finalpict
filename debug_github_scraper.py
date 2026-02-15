import requests
from bs4 import BeautifulSoup
import time

def scrape_github(username):
    print(f"Scraping GitHub for: {username}")
    
    # 1. Get Repositories (Sorted by Updated)
    url = f"https://github.com/{username}?tab=repositories&sort=updated"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch profile: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find repo links
        # GitHub structure: <h3 class="wb-break-all"> <a href="/user/repo" ...>
        repos = []
        repo_list = soup.find_all('h3', class_='wb-break-all')
        
        print(f"Found {len(repo_list)} repositories.")
        
        for r in repo_list[:3]: # Top 3
            link = r.find('a')
            if link:
                repo_name = link.text.strip()
                repo_url = f"https://github.com{link['href']}"
                print(f"  - Found Repo: {repo_name} ({repo_url})")
                
                # 2. Get README
                # Try raw content
                # Format: https://raw.githubusercontent.com/{username}/{repo_name}/main/README.md
                readme_content = ""
                branches = ["main", "master"]
                for branch in branches:
                    raw_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/{branch}/README.md"
                    try:
                        rr = requests.get(raw_url, headers=headers)
                        if rr.status_code == 200:
                            readme_content = rr.text[:1000] + "..." # Truncate
                            print(f"    -> Found README on branch '{branch}'")
                            break
                    except:
                        pass
                
                if not readme_content:
                    print("    -> No README found.")
                    
                repos.append({
                    "name": repo_name,
                    "url": repo_url,
                    "readme": readme_content
                })
                
                time.sleep(0.5) # Be nice
                
        return repos

    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    # Test with user's handle
    data = scrape_github("Shourya3126")
    print("\n--- Extracted Data ---")
    for d in data:
        print(f"Project: {d['name']}")
        print(f"README Preview: {d['readme'][:50].replace(chr(10), ' ')}...")
