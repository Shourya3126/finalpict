import requests
from bs4 import BeautifulSoup
import pdfplumber
import docx
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.service import Service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeParser:
    """Parses resumes from PDF and DOCX files."""
    
    @staticmethod
    def extract_text(file_path_or_buffer, file_type):
        text = ""
        try:
            if file_type == "pdf":
                with pdfplumber.open(file_path_or_buffer) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
            elif file_type == "docx":
                doc = docx.Document(file_path_or_buffer)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            else:
                return "Unsupported file format."
        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return f"Error parsing file: {str(e)}"
            
        return text.strip()

class WebScraper:
    """Scrapes content from websites, with specific handling for LinkedIn."""
    
    # LinkedIn UI noise lines to filter out
    NOISE_LINES = [
        "0 notifications", "Home", "My Network", "Jobs", "Messaging",
        "Notifications", "Me", "For Business", "Try Premium", "Try Premium for",
        "Post", "Write an article", "Add a photo", "Add a video",
        "Send", "More", "Open to", "Add profile section", "Enhance profile",
        "Accessibility", "Talent Solutions", "Community Guidelines", "Careers",
        "Marketing Solutions", "Privacy & Terms", "Ad Choices", "Advertising",
        "Sales Solutions", "Mobile", "Small Business", "Safety Center",
        "LinkedIn Corporation", "Questions?", "Visit our Help Center",
        "Manage your account and privacy", "Go to your Settings",
        "Recommendation transparency", "Select language", "Status is online",
        "You are on the messaging overlay", "Compose message"
    ]
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.driver = None  # Reusable browser session
        self._logged_in = False

    def init_browser(self):
        """Initialize a single browser session for batch processing."""
        if self.driver:
            return  # Already initialized
        
        import pickle
        import os
        from selenium.webdriver.edge.options import Options as EdgeOptions

        options = EdgeOptions()
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # STABILITY OPTIONS
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3") 
        
        # NETWORK / SSL FIXES
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-extensions")
        options.add_argument("--proxy-server='direct://'")
        options.add_argument("--proxy-bypass-list=*")
        options.add_argument("--start-maximized")

        logger.info("Initializing Microsoft Edge Driver (persistent session)...")
        self.driver = webdriver.Edge(options=options)
        
        # --- COOKIE HANDLING ---
        cookie_path = os.path.join(os.getcwd(), "linkedin_cookies.pkl")
        
        # Go to domain first
        self.driver.get("https://www.linkedin.com")
        
        if os.path.exists(cookie_path):
            logger.info(f"Loading cookies from {cookie_path}...")
            try:
                self.driver.delete_all_cookies()
                cookies = pickle.load(open(cookie_path, "rb"))
                for cookie in cookies:
                    if "linkedin" in cookie.get("domain", ""):
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            pass
                self.driver.refresh()
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Cookie load failed: {e}")

        # Verify Login
        if not self._check_login_status():
            logger.warning("Session not active. Waiting for manual login...")
            print(">>> PLEASE LOG IN MANUALLY NOW. (Script is watching for '/feed' or Nav Bar) <<<")
            
            max_wait = 600  # 10 mins
            start_time = time.time()
            while time.time() - start_time < max_wait:
                if self._check_login_status():
                    logger.info(f"Login verified! Saving cookies...")
                    pickle.dump(self.driver.get_cookies(), open(cookie_path, "wb"))
                    break
                time.sleep(1)
        
        self._logged_in = True

    def close_browser(self):
        """Properly close the browser session."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            self._logged_in = False
            logger.info("Browser session closed.")

    def _check_login_status(self):
        """Check if we are logged into LinkedIn."""
        try:
            d = self.driver
            curr = d.current_url
            tit = d.title
            if "authwall" in curr or "login" in curr or "ua/sign-in" in curr:
                return False
            if "/feed" in curr:
                return True
            if "/in/" in curr and "Sign In" not in tit and "Join" not in tit:
                return True
            if d.find_elements(By.ID, "global-nav") or d.find_elements(By.CLASS_NAME, "global-nav__content"):
                return True
            return False
        except:
            return False

    def _filter_noise(self, text):
        """Remove LinkedIn navbar/UI noise and sidebar 'People also viewed' from scraped text."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Stop if we hit the footer language selector or copyright
            if "Select language" in stripped or "LinkedIn Corporation" in stripped:
                break
                
            # Filter known noise
            if any(stripped.startswith(noise) for noise in self.NOISE_LINES):
                continue
                
            # Filter connection degree lines
            if "· 1st" in stripped or "· 2nd" in stripped or "· 3rd" in stripped:
                continue
            
            # "Follow" button = sidebar profile entry. Remove preceding name + headline.
            if stripped == "Follow":
                if len(cleaned) >= 2:
                    cleaned.pop()  # headline
                    cleaned.pop()  # name
                elif len(cleaned) >= 1:
                    cleaned.pop()
                continue
            
            # "Show more" / "Load more" often follows remaining sidebar entries.
            # Remove trailing name+headline pairs (headline contains "|").
            if stripped in ("Show more", "Load more"):
                while len(cleaned) >= 2:
                    last = cleaned[-1].strip()
                    second_last = cleaned[-2].strip()
                    if ('|' in last
                        and len(second_last.split()) <= 5
                        and second_last[:1].isupper()
                        and not second_last.startswith('===')):
                        cleaned.pop()  # headline
                        cleaned.pop()  # name
                    else:
                        break
                continue
            
            # Skip standalone "About" (sidebar footer link, not section marker)
            if stripped == "About":
                continue
                
            if stripped.isdigit() and len(stripped) <= 2:
                continue
            
            cleaned.append(line)
        return '\n'.join(cleaned)

    def _random_delay(self, min_s=2, max_s=5):
        """Add a randomized delay to mimic human browsing."""
        import random
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)

    def scrape_url(self, url):
        """Decides whether to use simple requests or Selenium based on the URL."""
        if "linkedin.com/in/" in url:
            return self.scrape_linkedin_selenium(url)
        else:
            return self.scrape_generic(url)

    def scrape_generic(self, url):
        """Simple requests-based scraper for static sites."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text
        except Exception as e:
            logger.error(f"Generic scrape error: {e}")
            return f"Failed to scrape {url}: {str(e)}"

    def scrape_linkedin_selenium(self, url):
        """
        Uses Selenium with Microsoft Edge to scrape LinkedIn profiles.
        Reuses a persistent browser session for batch efficiency.
        """
        import pickle
        import os

        # Initialize browser if not already done
        if not self.driver:
            self.init_browser()

        full_text_content = ""
        
        try:
            # Navigate to profile
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            self._random_delay(4, 6)
            
            # Check for authwall
            if "authwall" in self.driver.current_url or "signup" in self.driver.current_url:
                logger.warning("Hit authwall. Refreshing...")
                self.driver.refresh()
                self._random_delay(4, 6)
            
            # --- TARGETED SCRAPING STRATEGY ---
            logger.info("Starting targeted extraction...")
            
            # Wait for main profile to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Expand all "See more" buttons first
            try:
                self.driver.execute_script("""
                    document.querySelectorAll('.inline-show-more-text__button').forEach(b => b.click());
                    document.querySelectorAll('.pv-profile-section__see-more-inline').forEach(b => b.click());
                """)
                time.sleep(2)
            except:
                pass

            # --- DEEP SECTION SCRAPING (Sub-pages) ---
            def scrape_section(section_name, slug_suffix, retry_count=1):
                for attempt in range(retry_count + 1):
                    try:
                        clean_base = url.split("?")[0].rstrip("/")
                        section_url = f"{clean_base}/details/{slug_suffix}/"
                        
                        logger.info(f"Scraping {section_name}: {section_url}")
                        self.driver.get(section_url)
                        self._random_delay(2, 4)
                        
                        if self.driver.current_url == clean_base or "404" in self.driver.title:
                            logger.info(f"Section {section_name} not found or empty.")
                            return ""
                        
                        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        
                        # Scroll to load all items
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        
                        # Scrape the main list container
                        content = ""
                        try:
                            main_el = self.driver.find_element(By.CLASS_NAME, "scaffold-layout__main")
                            content = main_el.text
                        except:
                            content = self.driver.find_element(By.TAG_NAME, "body").text
                        
                        # Filter noise at scrape time
                        content = self._filter_noise(content)
                        
                        # Check if we got useful content or just noise
                        if len(content.strip()) < 10:
                            if attempt < retry_count:
                                logger.warning(f"Section {section_name} looks empty, retrying...")
                                self._random_delay(3, 5)
                                continue
                            return ""
                        
                        return f"=== {section_name.upper()} ===\n{content}\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to scrape {section_name} (attempt {attempt+1}): {e}")
                        if attempt < retry_count:
                            self._random_delay(3, 5)
                return ""

            # Scrape sections with retry
            full_text_content += scrape_section("Experience", "experience")
            full_text_content += scrape_section("Education", "education")
            full_text_content += scrape_section("Skills", "skills")
            full_text_content += scrape_section("Certifications", "certifications")

            # Main Profile (Header/About)
            logger.info("Scraping Main Header & About...")
            self.driver.get(url)
            self._random_delay(2, 4)
            
            profile_header = ""
            try:
                top_card = self.driver.find_element(By.CSS_SELECTOR, ".pv-top-card")
                profile_header += self._filter_noise(top_card.text) + "\n"
            except:
                pass
                
            try:
                about_section = self.driver.find_element(By.ID, "about")
                profile_header += "=== ABOUT ===\n" + self.driver.find_element(By.CSS_SELECTOR, "div.pv-shared-text-with-see-more").text
            except:
                pass
                
            full_text_content = f"=== PROFILE HEADER ===\n{profile_header}\n\n" + full_text_content
            
            # Save debug
            with open("last_scraped_profile.txt", "w", encoding="utf-8") as f:
                f.write(full_text_content)

            # --- POSTS SCRAPING ---
            if "/in/" in url:
                try:
                    base_url = url.split("?")[0].rstrip("/")
                    posts_url = f"{base_url}/recent-activity/all/"
                    logger.info(f"Checking posts: {posts_url}")
                    
                    self.driver.get(posts_url)
                    self._random_delay(2, 4)
                    
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    posts = []
                    selectors = [
                        "li.profile-creator-shared-feed-update__container",
                        "div.feed-shared-update-v2", 
                        "div.occludable-update"
                    ]
                    
                    feed_items = []
                    for sel in selectors:
                        feed_items = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        if feed_items:
                            break
                        
                    for item in feed_items[:5]:
                        try:
                            text = item.text.strip()
                            clean_lines = []
                            for line in text.split('\n'):
                                lower = line.lower()
                                if "likes" in lower or "comments" in lower or "repost" in lower or "followers" in lower:
                                    continue
                                clean_lines.append(line)
                            posts.append("\n".join(clean_lines))
                        except:
                            pass
                            
                    if posts:
                        posts_text = "\n---\n".join(posts)
                        with open("last_scraped_posts.txt", "w", encoding="utf-8") as f:
                            f.write(posts_text)
                        full_text_content += f"=== RECENT_POSTS ===\n{posts_text}"
                    else:
                        full_text_content += "=== RECENT_POSTS ===\n(No recent posts found)"
                         
                except Exception as e:
                    logger.warning(f"Could not scrape posts: {e}")

            return full_text_content

        except Exception as e:
            logger.error(f"Selenium error: {e}")
            return f"Error scraping LinkedIn: {str(e)}"

    def draft_linkedin_message(self, profile_url, message_text):
        """
        Navigates to profile, clicks 'Message', and types the draft.
        """
        import random
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.edge.options import Options as EdgeOptions
        
        options = EdgeOptions()
        options.add_experimental_option("detach", True) # Essential
        options.add_argument("--start-maximized")
        
        # Re-initialize driver for drafting action
        d = webdriver.Edge(options=options)
        
        try:
            # Quick Login Restore
            d.get("https://www.linkedin.com")
            cookie_path = os.path.join(os.getcwd(), "linkedin_cookies.pkl")
            if os.path.exists(cookie_path):
                d.delete_all_cookies()
                cookies = pickle.load(open(cookie_path, "rb"))
                for c in cookies:
                    if "linkedin" in c.get("domain", ""):
                        try: d.add_cookie(c)
                        except: pass
                d.refresh()
            
            d.get(profile_url)
            time.sleep(3)
            
            # --- STRATEGY 1: Direct URL via URN (Most Robust) ---
            import re
            
            # Look for the fsd_profile URN in the source
            # Pattern: urn:li:fsd_profile:ACoAA... (often caught in quotes)
            match = re.search(r'urn:li:fsd_profile:([A-Za-z0-9_-]+)', d.page_source)
            
            if match:
                urn_id = match.group(1)
                direct_url = f"https://www.linkedin.com/messaging/compose/?recipient={urn_id}"
                logger.info(f"Checking Direct Message URL: {direct_url}")
                d.get(direct_url)
                
            else:
                # --- STRATEGY 2: Button Click (Fallback) ---
                logger.info("URN not found, falling back to button click...")
                clicked = False
                selectors = [
                     "button.message-anywhere-button", 
                     "//button[contains(text(), 'Message')]",
                     ".pv-top-card-v2-ctas button.artdeco-button--primary"
                ]
                
                for sel in selectors:
                    try:
                        if "//" in sel: # XPath
                            btn = d.find_element(By.XPATH, sel)
                        else:
                            btn = d.find_element(By.CSS_SELECTOR, sel)
                        
                        btn.click()
                        clicked = True
                        break
                    except:
                        continue
                if not clicked:
                    return "Could not find 'Message' button or URN. You might need to connect first."

            # Wait for chat box to be ready
            time.sleep(4)
            found_box = None
            
            # Selectors for the chat box (Overlay vs Full Page vs Old UI)
            box_selectors = [
                "div.msg-form__contenteditable",
                "div[role='textbox'][aria-label*='Write']",
                "div[role='textbox']",
                ".msg-form__message-texteditor"
            ]
            
            for sel in box_selectors:
                try:
                    found_box = WebDriverWait(d, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    if found_box:
                        break
                except:
                    continue
            
            if found_box:
                # Use ActionChains to ensure focus
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(d)
                actions.move_to_element(found_box).click().perform()
                time.sleep(0.5)
                
                # Check formatting - strictly plain text
                lines = message_text.split('\n')
                for line in lines:
                    found_box.send_keys(line)
                    # Shift+Enter for new line in LinkedIn (Enter usually sends)
                    found_box.send_keys(Keys.SHIFT, Keys.ENTER)
                    time.sleep(random.uniform(0.01, 0.03)) 
                
                return "Drafted! Please review and click Send."
            else:
                # Fallback: Copy to clipboard
                import pyperclip
                pyperclip.copy(message_text)
                return "Could not find chat box to type. Message COPIED to Clipboard! Just Ctrl+V."


        except Exception as e:
            return f"Error: {e}"
