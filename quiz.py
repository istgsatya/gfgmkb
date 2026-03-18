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

class GFGQuizAutomator:
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
            
            # --- QUIZ SPECIFIC SELECTORS ---
            'mcq_sidebar_tab': (By.XPATH, "//div[contains(@class, 'sidebar_tabs') and p[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mcq') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'quiz')]]"),
            
            # Action Selectors
            'action_button': (By.XPATH, "//button[normalize-space()='Submit Response' or normalize-space()='Submitted']"),
            
            # Attacking the custom GFG div instead of standard radio buttons
            'first_option_label': (By.XPATH, "(//div[contains(@class, 'QuizRadioBtn_radio_container')])[1]"),
            
            'next_btn': (By.XPATH, "//button[contains(., 'Next')]"),
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

        logging.info("Initializing Selenium for Quizzes...")
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

    def login_check(self):
        self.driver.get(self.course_dashboard_url)
        try:
            self.long_wait.until(EC.presence_of_element_located(self.SELECTORS['accordion_arrow']))
            logging.info("Course dashboard loaded successfully.")
        except TimeoutException:
            logging.warning("Please log in manually within the next 120 seconds.")
            WebDriverWait(self.driver, 120).until(EC.presence_of_element_located(self.SELECTORS['accordion_arrow']))
            logging.info("Manual login detected. Proceeding.")

    def get_valid_tab_menus(self):
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

    def master_navigation_loop(self):
        self.wait.until(EC.presence_of_all_elements_located(self.SELECTORS['accordion_arrow']))
        time.sleep(2)
        
        accordions_raw = self.driver.find_elements(*self.SELECTORS['accordion_arrow'])
        total_acc = len(accordions_raw)
        accordions_to_process = min(7, total_acc) 
        
        logging.info(f"Quiz Bot Locked. Processing {accordions_to_process} sections in DESCENDING order.")
        
        # --- THE FIX: Iterating backwards from Bottom (Section 7) to Top (Section 1) ---
        for acc_idx in range(accordions_to_process - 1, -1, -1):
            logging.info(f"--- Focusing strictly on Section {acc_idx + 1} of {accordions_to_process} ---")
            self.exhaust_accordion(acc_idx)
            
        logging.info("QUIZ WORKFLOW COMPLETE! Target sections exhausted.")

    def exhaust_accordion(self, acc_idx):
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
                    
                    if self.scan_and_process_rows(parent_div):
                        accordion_still_has_work = True
                        break 
                
                if not accordion_still_has_work:
                    logging.info(f"All quiz tabs in '{section_title}' fully exhausted!")
                    return 

            else:
                logging.info(f"Scanning rows in '{section_title}'")
                if self.scan_and_process_rows(parent_div):
                    pass 
                else:
                    logging.info(f"All quiz rows in '{section_title}' fully exhausted!")
                    return 

    def scan_and_process_rows(self, container_div):
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

            try:
                meta_elem = row.find_element(*self.SELECTORS['item_meta'])
                meta_text = meta_elem.text.upper()
                
                # STRICT FILTER: Only enter if it explicitly has MCQs or Quiz
                if "MCQ" not in meta_text and "QUIZ" not in meta_text:
                    self.completed_sub_sections.add(row_title)
                    continue
            except NoSuchElementException:
                continue 

            try:
                btn = row.find_element(*self.SELECTORS['resume_button'])
                logging.info(f"Target Quiz Section Found: '{row_title}'. Entering player...")
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                btn.click()
                time.sleep(3) 
                
                self.solve_quiz_in_player(row_title)
                self.escape_to_dashboard()
                
                self.completed_sub_sections.add(row_title)
                return True 
                
            except Exception as e:
                logging.error(f"Failed to interact with row '{row_title}': {str(e)}")
                continue
                
        return False

    def solve_quiz_in_player(self, row_title):
        logging.info(f"Switching to MCQ/Quiz tab for '{row_title}'...")
        self.inject_anti_pause_script()

        try:
            quiz_tab = self.fast_wait.until(EC.element_to_be_clickable(self.SELECTORS['mcq_sidebar_tab']))
            quiz_tab.click()
            time.sleep(2) 
        except TimeoutException:
            logging.warning(f"No 'MCQ/Quiz' sidebar tab found. Assuming it's already on the quiz page.")
            pass

        question_number = 1

        while True:
            # --- THE FIX: 20 Question Killswitch ---
            if question_number > 20:
                logging.warning(f"Reached {question_number} questions. Triggering 20-question killswitch and escaping.")
                break

            logging.info(f"Checking Question #{question_number} state...")
            time.sleep(2) 
            
            try:
                action_btn = self.fast_wait.until(EC.presence_of_element_located(self.SELECTORS['action_button']))
                btn_text = action_btn.text.strip()
            except TimeoutException:
                logging.info("Could not find the Submit button. Assuming quiz is completed or broken.")
                break

            if btn_text == "Submitted":
                logging.info(f"Question already 'Submitted'. Skipping to Next.")
            else:
                logging.info(f"Question needs answering (State: '{btn_text}'). Clicking the first option...")
                try:
                    # Finds the GFG custom div and clicks it natively
                    first_label = self.driver.find_element(*self.SELECTORS['first_option_label'])
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_label)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", first_label)
                    time.sleep(1) 
                except NoSuchElementException:
                    logging.error("Failed to find any clickable options for this question.")
                    break

                try:
                    self.driver.execute_script("arguments[0].click();", action_btn)
                    logging.info("Smashed 'Submit Response'.")
                    
                    WebDriverWait(self.driver, 5).until(
                        EC.text_to_be_present_in_element(self.SELECTORS['action_button'], "Submitted")
                    )
                except Exception as e:
                    logging.warning(f"Submission verification lag or error: {e}")

            try:
                next_btn = self.driver.find_element(*self.SELECTORS['next_btn'])
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", next_btn)
                question_number += 1
            except NoSuchElementException:
                logging.info(f"No 'Next' button found. Quiz for '{row_title}' is 100% Complete!")
                break

    def escape_to_dashboard(self):
        logging.info("Clicking the GFG Back Button to return to dashboard...")
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
    bot = GFGQuizAutomator()
    bot.start()
