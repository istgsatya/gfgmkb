import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)

class GFGVideoAutomator:
    def __init__(self):
        self.course_dashboard_url = "https://www.geeksforgeeks.org/batch/dsa-juet-guna?tab=Resources" 
        
        self.driver = self._setup_driver()
        self.fast_wait = WebDriverWait(self.driver, 5) 
        self.wait = WebDriverWait(self.driver, 15)      
        self.long_wait = WebDriverWait(self.driver, 60) 
        
        # --- BOT MEMORY ---
        self.completed_sub_sections = set() 
        
        self.SELECTORS = {
            'accordion_arrow': (By.CSS_SELECTOR, 'div[class*="batch_arrow_icon"]'),
            
            # Sub-section Row Selectors
            'batch_item': (By.CSS_SELECTOR, 'div[class*="batch_item__"]'),
            'item_title': (By.CSS_SELECTOR, 'div[class*="batch_title_publish_container__"]'),
            'item_meta': (By.CSS_SELECTOR, 'div[class*="batch_content_meta__"]'),
            'resume_button': (By.CSS_SELECTOR, 'button[class*="batch_track_progress__btn"]'),
            
            # Horizontal Tabs
            'tab_menu_container': (By.CSS_SELECTOR, 'div[class*="ui pointing secondary menu"]'),
            'tab_item': (By.CSS_SELECTOR, 'a.item'),
            
            # Player UI
            'video_sidebar_tab': (By.XPATH, "//div[contains(@class, 'sidebar_tabs') and p[contains(text(), 'videos')]]"),
            'sidebar_video_item': (By.CSS_SELECTOR, 'a[class*="sidebar_item"]'),
            'back_to_home_btn': (By.CSS_SELECTOR, 'p[class*="sidebar_backTo_home"]')
        }

    def _setup_driver(self):
        options = Options()
        options.binary_location = '/usr/bin/chromium'
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222") 
        
        profile_path = os.path.abspath("./gfg_chrome_profile")
        options.add_argument(f"user-data-dir={profile_path}")

        logging.info("Initializing Selenium (Using Auto-Selenium Manager)...")
        driver = webdriver.Chrome(options=options)
        return driver

    def inject_anti_pause_script(self):
        script = """
            try {
                if (!window.visibilitySpoofed) {
                    Object.defineProperty(document, 'visibilityState', {get: function () { return 'visible'; }, configurable: true});
                    Object.defineProperty(document, 'hidden', {get: function () { return false; }, configurable: true});
                    window.visibilitySpoofed = true;
                }
                document.dispatchEvent(new Event('visibilitychange'));
            } catch(e) {}
        """
        self.driver.execute_script(script)

    def force_video_restart(self):
        logging.info("Attempting to force video to start from 0:00...")
        script = """
            let v = document.querySelector('video');
            if(v) {
                v.currentTime = 0;
                v.play();
                return true;
            }
            return false;
        """
        for _ in range(5):
            success = self.driver.execute_script(script)
            if success:
                logging.info("SUCCESS: Video reset to 0:00 and is playing.")
                return
            time.sleep(1)
        logging.warning("Could not find the HTML5 <video> tag.")

    def is_video_completed(self, video_element):
        try:
            images = video_element.find_elements(By.TAG_NAME, 'img')
            for img in images:
                src = img.get_attribute('src')
                if src and 'Group11(1)' in src:
                    return True
        except NoSuchElementException:
            pass
        try:
            progress = video_element.find_element(By.CSS_SELECTOR, 'div[class*="ui progress"]')
            if progress.get_attribute('data-percent') == '100':
                return True
        except NoSuchElementException:
            pass
        return False

    def login_check(self):
        self.driver.get(self.course_dashboard_url)
        try:
            self.long_wait.until(EC.presence_of_element_located(self.SELECTORS['accordion_arrow']))
            logging.info("Course dashboard loaded successfully.")
        except TimeoutException:
            logging.warning("Please log in manually in the browser window within the next 120 seconds.")
            WebDriverWait(self.driver, 120).until(EC.presence_of_element_located(self.SELECTORS['accordion_arrow']))
            logging.info("Manual login detected. Proceeding.")

    def get_valid_tab_menus(self):
        """Fetches tab menus but strictly ignores the main site navigation bar."""
        raw_menus = self.driver.find_elements(*self.SELECTORS['tab_menu_container'])
        valid_menus = []
        for m in raw_menus:
            if m.is_displayed():
                text = m.text.upper()
                if "RESOURCES" in text or "CONTEST" in text or "LEADERBOARD" in text:
                    continue
                valid_menus.append(m)
        return valid_menus

    def start(self):
        try:
            self.login_check()
            self.master_navigation_loop()
        except Exception as e:
            logging.critical(f"A critical error occurred: {str(e)}")
        finally:
            self.teardown()

    # --- THE STRICT HIERARCHICAL DRILL-DOWN & SECTION LIMIT ---
    def master_navigation_loop(self):
        """Iterates through accordions sequentially. Capped at Section 7."""
        self.wait.until(EC.presence_of_all_elements_located(self.SELECTORS['accordion_arrow']))
        time.sleep(2)
        
        # --- CHANGED: Hardcoded Limit based on user request ---
        # Before: processed accordions_count = len(...)
        # Now: Limits strictly to the first 7 sections (skipping bottom 2 mock tests).
        accordions_raw = self.driver.find_elements(*self.SELECTORS['accordion_arrow'])
        total_acc = len(accordions_raw)
        
        # Ensure we don't try to process more sections than exist if the course is small.
        accordions_to_process = min(7, total_acc) 
        
        logging.info(f"Base Code Locked. Strict workflow set to process first {accordions_to_process} of {total_acc} total sections.")
        
        for acc_idx in range(accordions_to_process):
            logging.info(f"--- Focusing strictly on Section {acc_idx + 1} of 7 ---")
            self.exhaust_accordion(acc_idx)
            
        logging.info("STRICT WORKFLOW COMPLETE! First 7 sections exhausted.")

    def exhaust_accordion(self, acc_idx):
        """Stays locked inside a single accordion until every tab and row is 100% completed."""
        while True:
            self.wait.until(EC.presence_of_all_elements_located(self.SELECTORS['accordion_arrow']))
            time.sleep(2)
            arrows = self.driver.find_elements(*self.SELECTORS['accordion_arrow'])
            if acc_idx >= len(arrows): return

            arrow = arrows[acc_idx]
            parent_div = arrow.find_element(By.XPATH, "./../..")
            
            try:
                section_title = parent_div.text.split('\n')[0].strip()
            except:
                section_title = f"Section {acc_idx + 1}"

            # Ensure Accordion is Open
            if "batch_open" not in parent_div.get_attribute("class"):
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", arrow)
                time.sleep(0.5)
                arrow.click()
                time.sleep(1.5)

            menus = self.get_valid_tab_menus()

            if menus:
                tabs = menus[0].find_elements(*self.SELECTORS['tab_item'])
                tab_count = len(tabs)
                accordion_still_has_work = False

                for tab_idx in range(tab_count):
                    fresh_menus = self.get_valid_tab_menus()
                    if not fresh_menus: break
                    fresh_tabs = fresh_menus[0].find_elements(*self.SELECTORS['tab_item'])
                    if tab_idx >= len(fresh_tabs): break

                    tab = fresh_tabs[tab_idx]
                    tab_name = tab.text.strip()

                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
                    time.sleep(0.5)
                    tab.click()
                    time.sleep(1.5)
                    
                    logging.info(f"Scanning Tab: [{tab_name}] in '{section_title}'")
                    
                    # Pass the specific parent_div to ensure it ONLY looks at rows inside this accordion
                    if self.scan_and_process_rows(parent_div):
                        accordion_still_has_work = True
                        break # Break tab loop -> Restarts while loop to process next row in this tab
                
                if not accordion_still_has_work:
                    logging.info(f"All tabs in '{section_title}' are fully exhausted!")
                    return # Exit while loop -> Allows master loop to move to NEXT accordion

            else:
                # No tabs, just rows
                logging.info(f"Scanning rows in '{section_title}'")
                if self.scan_and_process_rows(parent_div):
                    pass # Loop again to check remaining rows
                else:
                    logging.info(f"All rows in '{section_title}' are fully exhausted!")
                    return # Exit while loop -> Allows master loop to move to NEXT accordion

    def scan_and_process_rows(self, container_div):
        """Scans rows strictly inside the provided container_div. Cannot jump to other sections."""
        rows = container_div.find_elements(*self.SELECTORS['batch_item'])
        visible_rows = [r for r in rows if r.is_displayed()]
        
        for row in visible_rows:
            try:
                title_elem = row.find_element(*self.SELECTORS['item_title'])
                row_title = title_elem.text.strip().split('\n')[0]
            except Exception:
                continue

            if row_title in self.completed_sub_sections:
                continue

            # Strict "Contains Videos" Check
            # Based on User Images 1 & 2: Handles rows like "dsa why and how" but skips pure "quiz"
            try:
                meta_elem = row.find_element(*self.SELECTORS['item_meta'])
                meta_text = meta_elem.text
                
                if "Video" not in meta_text:
                    logging.info(f"Skipping '{row_title}' -> No videos detected in metadata.")
                    self.completed_sub_sections.add(row_title)
                    continue
            except NoSuchElementException:
                continue 

            # Target Found!
            try:
                btn = row.find_element(*self.SELECTORS['resume_button'])
                logging.info(f"Target Sub-Section Found: '{row_title}'. Entering player...")
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                btn.click()
                time.sleep(3) 
                
                self.watch_videos_in_player(row_title)
                self.escape_to_dashboard()
                
                self.completed_sub_sections.add(row_title)
                return True 
                
            except Exception as e:
                logging.error(f"Failed to interact with row '{row_title}': {str(e)}")
                continue
                
        return False

    def watch_videos_in_player(self, row_title):
        try:
            video_tab = self.fast_wait.until(EC.element_to_be_clickable(self.SELECTORS['video_sidebar_tab']))
            video_tab.click()
            time.sleep(2) 
        except TimeoutException:
            logging.warning(f"No 'Videos' sidebar tab found in '{row_title}'. Completing early.")
            return

        self.inject_anti_pause_script()
        first_video_played = False

        while True:
            try:
                self.wait.until(EC.presence_of_all_elements_located(self.SELECTORS['sidebar_video_item']))
            except TimeoutException:
                break
                
            sidebar_videos = self.driver.find_elements(*self.SELECTORS['sidebar_video_item'])
            
            next_uncompleted_video = None
            target_index = -1
            
            for index, video_element in enumerate(sidebar_videos):
                if self.is_video_completed(video_element):
                    continue 
                    
                next_uncompleted_video = video_element
                target_index = index
                break
            
            if not next_uncompleted_video:
                logging.info(f"All videos in '{row_title}' are 100% complete!")
                break 

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_uncompleted_video)
            time.sleep(1) 
            self.driver.execute_script("arguments[0].click();", next_uncompleted_video)
            time.sleep(3)
            
            if not first_video_played:
                logging.info("Executing User Hack: Clicking away and back to force autoplay...")
                try:
                    if target_index + 1 < len(sidebar_videos):
                        temp_video = sidebar_videos[target_index + 1]
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", temp_video)
                        self.driver.execute_script("arguments[0].click();", temp_video)
                        time.sleep(3) 
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_uncompleted_video)
                        self.driver.execute_script("arguments[0].click();", next_uncompleted_video)
                        time.sleep(3)
                except Exception:
                    pass
                first_video_played = True

            self.force_video_restart()

            logging.info("Video playback in progress. Entering 15-second monitoring loop...")
            while True:
                time.sleep(15) 
                self.inject_anti_pause_script() 
                
                try:
                    clean_current_video = self.driver.find_elements(*self.SELECTORS['sidebar_video_item'])[target_index]
                    if self.is_video_completed(clean_current_video):
                        logging.info("Ding! Video marked as complete by GFG. Moving to next.")
                        break
                except Exception:
                    pass

    def escape_to_dashboard(self):
        logging.info("Clicking the GFG Back Button to return to the sub-section list...")
        try:
            back_btn = self.wait.until(EC.element_to_be_clickable(self.SELECTORS['back_to_home_btn']))
            self.driver.execute_script("arguments[0].click();", back_btn)
            self.wait.until(EC.presence_of_element_located(self.SELECTORS['accordion_arrow']))
            time.sleep(2)
        except Exception as e:
            logging.error(f"Back button failed ({str(e)}). Forcing URL reload as fallback.")
            self.driver.get(self.course_dashboard_url)
            time.sleep(3)

    def teardown(self):
        logging.info("Automation session complete. Closing browser.")
        self.driver.quit()

if __name__ == "__main__":
    bot = GFGVideoAutomator()
    bot.start()
