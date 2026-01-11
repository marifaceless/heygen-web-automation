"""
HeyGen Batch Video Automation
=============================
Uses Playwright persistent context (profile-based approach).
Can run in headless or non-headless mode.

SETUP:
1. Run setup_profile.py first to create a logged-in Chrome profile
2. Then run this script for the full automation
"""

import os
import time
import json
import argparse
import sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ============================================
# CONFIGURATION - EDIT THESE PATHS
# ============================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(SCRIPT_DIR, "chrome_profile")
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Parent of HeadlessTest folder

# You can change these to your preferred locations
INPUT_FILES_DIR = os.path.join(BASE_DIR, "inputFiles")
OUTPUT_FILES_DIR = os.path.join(BASE_DIR, "outputFiles")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "tracking.json")

# Headless mode - set to True to run invisibly
RUN_HEADLESS = False       # Change to True once you confirm headless works

# Poll interval for checking new downloads (in seconds)
POLLING_SLEEP_SECONDS = 90


class HeyGenAutomation:
    def __init__(self):
        """Initialize automation paths, defaults, and required directories."""
        self.profile_dir = PROFILE_DIR
        self.input_files_dir = INPUT_FILES_DIR
        self.output_files_dir = OUTPUT_FILES_DIR
        self.tracking_file = TRACKING_FILE
        self.headless = RUN_HEADLESS
        
        # Create directories if needed
        os.makedirs(self.input_files_dir, exist_ok=True)
        os.makedirs(self.output_files_dir, exist_ok=True)
    
    # ============================================
    # JSON TRACKING FUNCTIONS
    # ============================================
    
    def load_tracking(self):
        """Load tracking data from JSON file"""
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading tracking file: {e}")
        return None
    
    def save_tracking(self, data):
        """Save tracking data to JSON file"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving tracking file: {e}")
            return False
    
    def load_config(self):
        """Load avatar configuration from config.txt"""
        config_path = os.path.join(os.path.dirname(self.tracking_file), "config.txt")
        avatars = []
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for line in content.splitlines():
                        if "available_avatars:" in line:
                            parts = line.split("available_avatars:")[1].split(",")
                            avatars = [nominal.strip() for nominal in parts if nominal.strip()]
            else:
                print(f"⚠️ config.txt not found at {config_path}")
        except Exception as e:
             print(f"⚠️ Error loading config.txt: {e}")
        return avatars

    def load_ui_queue(self, queue_path):
        """Load queue data created by the web UI"""
        try:
            if os.path.exists(queue_path):
                with open(queue_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            print(f"⚠️ UI queue not found at {queue_path}")
        except Exception as e:
            print(f"⚠️ Error loading UI queue: {e}")
        return None

    def create_new_tracking_session(self):
        """Create new tracking session structure"""
        return {
            "session_start": datetime.now().isoformat(),
            "projects": []
        }

    def add_project_to_tracking(self, tracking_data, project_name, heygen_folder_name, config):
        """Add a project to the current tracking session"""
        project_entry = {
            "project_name": project_name,
            "heygen_folder_name": heygen_folder_name,
            "started_at": datetime.now().isoformat(),
            "config": config,
            "videos": [],
            "status": "processing"
        }
        if "projects" not in tracking_data:
             tracking_data["projects"] = []
             
        tracking_data["projects"].append(project_entry)
        return project_entry

    def add_video_to_project(self, tracking_data, project_name, scene_folder, script_file, video_name):
        """Add video to a specific project in tracking"""
        for project in tracking_data.get("projects", []):
            if project["project_name"] == project_name:
                video_entry = {
                    "scene_folder": scene_folder,
                    "script_file": script_file,
                    "video_name": video_name,
                    "submitted_at": datetime.now().isoformat(),
                    "status": "processing",
                    "downloaded_at": None,
                    "output_file": None,
                    "error_message": None
                }
                project["videos"].append(video_entry)
                return video_entry
        return None

    def update_video_status(self, tracking_data, scene_folder, status, output_file=None, error_message=None):
        """Update status of a video in tracking (searches all projects)"""
        for project in tracking_data.get("projects", []):
            for video in project["videos"]:
                if video["scene_folder"] == scene_folder:
                    video["status"] = status
                    if status == "downloaded":
                        video["downloaded_at"] = datetime.now().isoformat()
                        video["output_file"] = output_file
                    if error_message:
                        video["error_message"] = error_message
                    return
    
    # ============================================
    # CLI / USER INPUT FUNCTIONS
    # ============================================
    
    def get_mode_selection(self):
        """Prompt user to select operation mode"""
        print("\n" + "="*60)
        print("🎬 HEYGEN BATCH VIDEO AUTOMATION")
        print("   (Persistent Context Mode)")
        print("="*60 + "\n")
        
        print(f"📁 Profile: {self.profile_dir}")
        print(f"🖥️ Mode: {'Headless' if self.headless else 'Visible'}")
        print("")
        
        print("Select operation mode:")
        print("  1. Submit new videos")
        print("  2. Check & download pending videos")
        print("  3. Submit & download (unattended overnight mode)")
        print("")
        
        while True:
            choice = input("👉 Enter your choice (1, 2, or 3): ").strip()
            if choice == "1":
                return "submit"
            elif choice == "2":
                return "download"
            elif choice == "3":
                return "unattended"
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3")
    
    def get_project_info(self):
        """
        Scan inputFiles for Projects and their Scenes
        Returns: (project_name, list of (scene_folder_name, script_path, script_filename))
        """
        try:
            input_path = Path(self.input_files_dir)
            
            # Get all project folders (first level)
            projects = [f for f in input_path.iterdir() if f.is_dir()]
            
            if not projects:
                raise Exception(f"No project folders found in {self.input_files_dir}")
        
            # Display projects with their scenes
            print("\n" + "="*60)
            print("📂 AVAILABLE PROJECTS")
            print("="*60 + "\n")
            
            project_info_list = [] # List of (project_obj, scenes_list)
            
            for idx, project in enumerate(projects, 1):
                # Get scene folders within this project
                scenes = [s for s in project.iterdir() if s.is_dir()]
                project_info_list.append((project, scenes))
                
                print(f"  {idx}. {project.name}")
                for scene in scenes:
                    # Find script file in scene
                    text_files = list(scene.glob("*.txt")) + list(scene.glob("*.text"))
                    script_status = f"({text_files[0].name})" if text_files else "(no script found)"
                    print(f"      └── {scene.name} {script_status}")
                print("")
        
            # Get user selection (Multi-select)
            selected_projects_data = [] # List of (project_name, scene_list)
            
            while True:
                try:
                    selection = input(f"👉 Select project (e.g. 1-3, '1,2', 'all'): ").strip().lower()
                    
                    indices = set()
                    if selection in ['all', 'a']:
                        indices = set(range(len(projects)))
                    else:
                        # Parse ranges and commas
                        parts = selection.replace(',', ' ').split()
                        for part in parts:
                            if '-' in part:
                                start, end = map(int, part.split('-'))
                                indices.update(range(start-1, end))
                            else:
                                indices.add(int(part) - 1)
                    
                    # Validate indices
                    valid_indices = [i for i in indices if 0 <= i < len(projects)]
                    
                    if not valid_indices:
                         print("❌ No valid projects selected.")
                         continue
                         
                    print(f"✅ Selected {len(valid_indices)} project(s).")
                    
                    for idx in sorted(valid_indices):
                        selected_project, scenes = project_info_list[idx]
                        
                        # Build scene list for this project
                        current_scene_list = []
                        for scene in scenes:
                            text_files = list(scene.glob("*.txt")) + list(scene.glob("*.text"))
                            if text_files:
                                script_file = text_files[0]
                                current_scene_list.append((scene.name, str(script_file), script_file.stem))
                        
                        if current_scene_list:
                             selected_projects_data.append((selected_project.name, current_scene_list))
                        else:
                            print(f"⚠️ Skipping {selected_project.name} (no scripts found)")
    
                    if not selected_projects_data:
                         print("❌ No valid scenes found in selected projects.")
                         continue
                         
                    break
    
                except ValueError:
                    print("❌ Invalid input format.")
            
            return selected_projects_data
            
        except Exception as e:
            print(f"❌ Error reading project info: {e}")
            raise
    
    def read_script_file(self, script_path):
        """Read the script content from file"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            print(f"❌ Error reading script file: {e}")
            raise

    def get_script_content(self, script_path, script_text):
        """Return script text from memory or file path"""
        if script_text is not None:
            return script_text
        return self.read_script_file(script_path)
    
    def get_user_preferences(self):
        """Get user preferences for video generation via CLI prompts"""
        print("\n" + "="*60)
        print("🎬 VIDEO CONFIGURATION (applies to all videos)")
        print("="*60 + "\n")
        
        # Get video quality
        while True:
            quality = input("📊 Select video quality (720p/1080p) [default: 720p]: ").strip().lower()
            if quality == "":
                quality = "720p"
                break
            elif quality in ["720p", "1080p"]:
                break
            else:
                print("❌ Invalid choice. Please enter '720p' or '1080p'")
        
        # Get FPS
        while True:
            fps = input("🎥 Select FPS (25/30/60) [default: 25]: ").strip()
            if fps == "":
                fps = "25"
                break
            elif fps in ["25", "30", "60"]:
                break
            else:
                print("❌ Invalid choice. Please enter 25, 30, or 60")
        
        # Get subtitle preference
        while True:
            subtitle = input("📝 Enable subtitles? (yes/no) [default: yes]: ").strip().lower()
            if subtitle == "":
                subtitle = "yes"
                break
            elif subtitle in ["yes", "y", "no", "n"]:
                subtitle = "yes" if subtitle in ["yes", "y"] else "no"
                break
            else:
                print("❌ Invalid choice. Please enter 'yes' or 'no'")
        
        print("\n" + "="*60)
        print("✅ Configuration Complete!")
        print(f"   Quality: {quality}")
        print(f"   FPS: {fps}")
        print(f"   Subtitles: {subtitle}")
        print("="*60 + "\n")
        
        return {"quality": quality, "fps": fps, "subtitles": subtitle, "avatar_name": None}
    
    # ============================================
    # BROWSER HELPER FUNCTIONS
    # ============================================
    
    def wait_for_latest_download(self, directory):
        """Watch a directory until a completed download appears."""
        print(f"🔍 Monitoring {directory} for new files (no timeout)...")
        start_time = time.time()

        while True:
            time.sleep(2)
            files = [os.path.join(directory, f) for f in os.listdir(directory)]
            if not files:
                continue

            latest_file = max(files, key=os.path.getmtime)
            
            if latest_file.endswith('.crdownload') or latest_file.endswith('.tmp'):
                print(f"⏳ File downloading: {os.path.basename(latest_file)}", end='\r')
                continue
                
            try:
                size1 = os.path.getsize(latest_file)
                time.sleep(2)
                size2 = os.path.getsize(latest_file)
                
                if size1 == size2 and size1 > 0:
                    if os.path.getmtime(latest_file) >= start_time:
                        return latest_file
            except:
                pass
                
        return None
    
    def launch_browser(self, playwright):
        """Launch browser with persistent context"""
        print(f"\n🚀 Launching browser ({'headless' if self.headless else 'visible'} mode)...")
        
        # Check if profile exists
        if not os.path.exists(self.profile_dir):
            print("❌ Chrome profile not found!")
            print(f"   Expected: {self.profile_dir}")
            print("   Please run setup_profile.py first.")
            return None
        
        browser_channel = os.getenv("HEYGEN_BROWSER_CHANNEL", "chrome").strip().lower()
        if browser_channel in {"", "chromium", "none"}:
            browser_channel = None

        launch_kwargs = dict(
            user_data_dir=self.profile_dir,
            headless=self.headless,
            downloads_path=self.output_files_dir,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1920, "height": 1080} if self.headless else None,
        )

        # Launch persistent context with preferred channel, then fall back if needed.
        try:
            context = playwright.chromium.launch_persistent_context(
                channel=browser_channel,
                **launch_kwargs,
            )
        except Exception as exc:
            if browser_channel:
                print(f"⚠️ Could not launch channel '{browser_channel}': {exc}")
                print("   Falling back to bundled Chromium...")
                context = playwright.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise

        self._grant_clipboard_permissions(context)

        self._install_rating_popup_watchdog(context)
        
        print("✅ Browser launched successfully!")
        return context
    
    def _get_or_create_page(self, context):
        """Get existing page or create a new one"""
        if len(context.pages) > 0:
            return context.pages[0]
        else:
            return context.new_page()

    def _install_rating_popup_watchdog(self, context):
        """Auto-dismiss the rating popup whenever it appears"""
        script = """
        (() => {
          const textNeedle = "How likely are you to recommend us";
          const buttonLabels = ["Not now", "No thanks", "Skip"];
          const closeLabels = ["Close", "Done", "OK", "Continue"];
          const tryDismiss = () => {
            const dialogs = document.querySelectorAll('div[role="dialog"], div.tw-stack-dialog, div.rc-dialog-wrap');
            for (const dialog of dialogs) {
              const text = dialog.innerText || "";
              if (!text.includes(textNeedle)) {
                continue;
              }
              const buttons = Array.from(dialog.querySelectorAll("button"));
              const target = buttons.find((btn) => {
                const label = (btn.getAttribute("aria-label") || "").toLowerCase();
                if (label.includes("close")) {
                  return true;
                }
                const btnText = (btn.innerText || "").trim();
                return buttonLabels.includes(btnText) || closeLabels.includes(btnText);
              });
              if (target) {
                target.click();
                return true;
              }
            }
            return false;
          };
          setInterval(tryDismiss, 1200);
        })();
        """
        try:
            context.add_init_script(script)
        except Exception as e:
            print(f"⚠️ Could not install popup watchdog: {e}")

    def _grant_clipboard_permissions(self, context):
        """Grant clipboard permissions for HeyGen origins where supported."""
        origins = [
            "https://app.heygen.com",
            "https://www.heygen.com",
        ]
        for origin in origins:
            try:
                context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
            except Exception as e:
                print(f"⚠️ Could not grant clipboard permissions for {origin}: {e}")
    
    # ============================================
    # SHARED HELPER METHODS (EXTRACTED FROM DUPLICATES)
    # ============================================
    
    def _sanitize_filename(self, filename):
        """Sanitize filename for Windows (replace invalid chars)"""
        return filename.replace('/', '-').replace(':', '-').replace('\\', '-').replace('|', '-')

    def _dismiss_modal_overlays(self, page, timeout_seconds=4):
        """Dismiss blocking overlays such as rating popups or modal backdrops."""
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        time.sleep(0.2)

        overlay_selectors = [
            "div.tw-stack-dialog",
            "div.rc-dialog-wrap",
            '[role="dialog"]',
        ]
        button_labels = ["Close", "Done", "OK", "Continue", "Not now", "No thanks", "Skip", "Cancel"]

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            for selector in overlay_selectors:
                try:
                    overlays = page.locator(selector)
                    count = overlays.count()
                    if count == 0:
                        continue
                    for i in range(min(count, 3)):
                        overlay = overlays.nth(i)
                        if not overlay.is_visible():
                            continue
                        for label in button_labels:
                            btn = overlay.locator(f'button:has-text("{label}")')
                            if btn.count() > 0 and btn.first.is_visible():
                                btn.first.click()
                                time.sleep(0.4)
                                return True
                        # fallback: click backdrop to dismiss
                        try:
                            overlay.click(position={"x": 10, "y": 10})
                            time.sleep(0.2)
                            return True
                        except Exception:
                            pass
                except Exception:
                    continue
            time.sleep(0.3)
        return False
    
    def _smart_truncate(self, text, limit=25000):
        """
        Truncate text to limit, but cut off at the last complete sentence.
        Returns the truncated text.
        """
        if len(text) <= limit:
            return text
            
        print(f"⚠️ Script exceeds {limit} characters (Total: {len(text)}). Truncating...")
        
        # Slice to the limit
        truncated = text[:limit]
        
        # List of sentence-ending punctuation
        # We look for the last occurrence of any of these
        endings = ['.', '!', '?', '\n']
        
        last_end = -1
        for char in endings:
            pos = truncated.rfind(char)
            if pos > last_end:
                last_end = pos
        
        if last_end != -1:
            # Cut at the punctuation (include it)
            final_text = truncated[:last_end+1]
        else:
            # Fallback if no sentence ending found (rare for 25k chars)
            final_text = truncated
            
        print(f"✂️  Truncated to {len(final_text)} characters (removed {len(text) - len(final_text)} chars)")
        return final_text

    def _dismiss_rating_popup(self, page):
        """Dismiss the HeyGen rating popup if it appears"""
        try:
            popup_text = page.locator('text=How likely are you to recommend us')
            if popup_text.count() == 0:
                return False

            dialog = page.locator('div[role="dialog"]').filter(has=popup_text)
            if dialog.count() == 0:
                dialog = page.locator('div:has-text("How likely are you to recommend us")').first

            if dialog.count() == 0 or not dialog.first.is_visible():
                return False

            print("🧹 Dismissing rating popup...")
            close_candidates = [
                'button[aria-label="Close"]',
                'button[aria-label="close"]',
                'button:has-text("Not now")',
                'button:has-text("No thanks")',
                'button:has-text("Skip")',
                'button:has(svg)',
            ]

            for selector in close_candidates:
                button = dialog.locator(selector)
                if button.count() > 0 and button.first.is_visible():
                    button.first.click()
                    time.sleep(0.4)
                    return True

            page.keyboard.press("Escape")
            time.sleep(0.2)
            page.mouse.click(10, 10)
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"⚠️ Could not dismiss rating popup: {e}")
            return False

    def _wait_for_ai_studio_editor(self, page, timeout_seconds=8):
        """Wait for AI Studio script editor to appear."""
        selectors = [
            'text=Type your script',
            'text=Type your script or',
            'span[data-node-view-content]',
            'div[contenteditable="true"]',
        ]

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0 and locator.first.is_visible():
                        return True
                except Exception:
                    pass
            time.sleep(0.4)
        return False

    def _click_first_visible(self, page, selectors, timeout_seconds=8):
        """Click the first visible selector in the list within the timeout."""
        deadline = time.time() + timeout_seconds
        last_error = None

        while time.time() < deadline:
            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() == 0:
                        continue
                    target = locator.first
                    if not target.is_visible():
                        continue
                    target.scroll_into_view_if_needed()
                    target.click(timeout=2000)
                    return selector
                except Exception as e:
                    last_error = e
            time.sleep(0.4)

        if last_error:
            print(f"⚠️ Could not click any selector: {last_error}")
        return None

    def _open_ai_studio(self, page):
        """Open AI Studio for the selected avatar, handling UI variations."""
        self._dismiss_rating_popup(page)
        time.sleep(1)
        # New UI: selecting an avatar can drop us directly into AI Studio.
        if self._wait_for_ai_studio_editor(page, timeout_seconds=5):
            return True

        direct_selectors = [
            'button:has-text("Create with AI Studio")',
            'text=/Create in AI studio/i',
            'button:has-text("AI Studio")',
            'a:has-text("AI Studio")',
            'button:has-text("Create video")',
            'button:has-text("Create Video")',
            'button:has-text("Use this avatar")',
            'button:has-text("Use avatar")',
        ]

        for selector in direct_selectors:
            if self._click_first_visible(page, [selector], timeout_seconds=5):
                if self._wait_for_ai_studio_editor(page):
                    return True

        menu_triggers = [
            'button:has-text("Create")',
            'button:has-text("New")',
        ]

        if self._click_first_visible(page, menu_triggers, timeout_seconds=4):
            time.sleep(0.6)
            menu_selectors = [
                'text=/Create in AI studio/i',
                '[role="menuitem"]:has-text("Create in AI studio")',
                '[role="menuitem"]:has-text("AI Studio")',
                'button:has-text("AI Studio")',
                'a:has-text("AI Studio")',
                'text=/AI Studio/i',
            ]
            if self._click_first_visible(page, menu_selectors, timeout_seconds=6):
                if self._wait_for_ai_studio_editor(page):
                    return True

        return False

    def _create_heygen_folder(self, page, heygen_folder_name):
        """Create a new folder on HeyGen (shared helper)"""
        print("📁 Creating project folder on HeyGen...")
        self._dismiss_rating_popup(page)
        
        page.locator('[data-testid="projects-menu"]').click()
        time.sleep(2)
        
        page.locator('//button[@title="New Folder"]').click()
        time.sleep(1)
        
        page.locator('//input[@placeholder="Enter folder name"]').fill(heygen_folder_name)
        time.sleep(1)
        
        page.locator('//button[normalize-space()="Save"]').click()
        time.sleep(2)
        print(f"✅ Folder created: '{heygen_folder_name}'")
    
    
    def _find_and_select_avatar(self, page, avatar_name_to_find):
        """Find avatar by name, scrolling if necessary"""
        print(f"🔍 Searching for avatar: '{avatar_name_to_find}'...")

        self._dismiss_modal_overlays(page)
        page.locator('[data-testid="my-avatars-menu"]').click()
        time.sleep(2)
        
        # Try to find exactly matching text first
        start_time = time.time()
        timeout = 30 # Search for up to 30 seconds
        found = False
        
        while time.time() - start_time < timeout:
            # Look for ANY element containing the name
            # We use a broad selector to catch the name on the card
            try:
                # Use XPath to find the specific card containing the text. 
                # We look for the card container class 'tw-rounded-[20px]' that HAS the text somewhere inside it.
                # This ensures we get the CLICKABLE card element, not just a random text span.
                xpath_selector = f'//div[contains(@class, "tw-rounded-[20px]") and .//text()[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{avatar_name_to_find.lower()}")]]'
                
                elements = page.locator(xpath_selector)
                
                count = elements.count()
                if count > 0:
                     # Check if any are visible
                     for i in range(count):
                         if elements.nth(i).is_visible():
                             print(f"   ✅ Found avatar '{avatar_name_to_find}'")
                             # Robust click sequence
                         card = elements.nth(i)
                         card.scroll_into_view_if_needed()
                         card.hover()
                         time.sleep(1)
                         try:
                             card.click(timeout=2000) # Short timeout for standard click
                         except Exception as e_click:
                             print(f"      ⚠️ Standard click failed: {e_click}")
                             try:
                                 print("      🔨 Trying force click...")
                                 card.click(force=True, timeout=2000)
                             except Exception as e_force:
                                 print(f"      ⚠️ Force click failed: {e_force}")
                                 print("      🧬 Trying JS dispatch click...")
                                 card.dispatch_event('click')

                         # New UI: confirm avatar selection via dialog
                         self._confirm_avatar_use_in_video(page)
                         return True
            except Exception as e_outer:
                # Only print if it's not a common "element not found" type error during iteration
                # print(f"   ⚠️ Search iteration error: {e_outer}")
                pass
                
            # Not found yet, scroll down
            print("   ⏬ Scrolling down...", end='\r')
            page.mouse.wheel(0, 1000)
            time.sleep(1)
            
        print(f"⚠️ Could not find avatar '{avatar_name_to_find}' after scrolling.")
        return False

    def _confirm_avatar_use_in_video(self, page):
        """Click the 'Use in video' dialog button if it appears after avatar selection."""
        dialog = page.locator("div.rc-dialog-wrap")
        button_selectors = [
            'button:has-text("Use in video")',
            'button:has-text("Use this avatar")',
            'button:has-text("Use avatar")',
        ]

        deadline = time.time() + 6
        while time.time() < deadline:
            try:
                if dialog.count() > 0 and dialog.first.is_visible():
                    for selector in button_selectors:
                        target = dialog.locator(selector)
                        if target.count() > 0 and target.first.is_visible():
                            target.first.click()
                            time.sleep(0.6)
                            try:
                                dialog.first.wait_for(state="hidden", timeout=4000)
                            except Exception:
                                pass
                            return True
            except Exception:
                pass
            time.sleep(0.4)
        return False

    def _submit_single_video(self, page, scene_folder, script_path, script_filename, config, heygen_folder_name, avatar_name, tracking_data, project_name, script_text=None):
        """Submit a single video to HeyGen (shared helper)
        Returns: True on success, False on failure
        """
        # Read script
        video_script = self.get_script_content(script_path, script_text)
        
        # Smart truncate if needed
        video_script = self._smart_truncate(video_script, limit=25000)
        
        print(f"📄 Script loaded: {len(video_script)} characters")
        
        # Select Avatar (Smart Search)
        print("👤 Opening avatar section...")
        if not self._find_and_select_avatar(page, avatar_name):
             print(f"❌ Failed to select avatar '{avatar_name}'. Skipping video.")
             return False
        
        time.sleep(2)
        print("✅ Avatar selected")
        
        # Click "Create with AI Studio"
        print("🎬 Opening AI Studio...")
        self._dismiss_modal_overlays(page)
        if not self._open_ai_studio(page):
            print("❌ Could not open AI Studio. UI may have changed.")
            return False
        print("✅ AI Studio opened")
        
        # Add Script using clipboard paste (ProseMirror requires this)
        print("📝 Adding script...")
        try:
            page.locator('text=Type your script or').click()
        except:
            page.locator('span[data-node-view-content]').first.click()
        
        time.sleep(0.5)
        
        # Select any existing content first
        modifier_key = "Meta" if sys.platform == "darwin" else "Control"
        page.keyboard.press(f"{modifier_key}+a")
        time.sleep(0.2)
        
        # Copy script to clipboard and paste it (ProseMirror handles paste events properly)
        paste_ok = False
        try:
            page.evaluate("""(text) => navigator.clipboard.writeText(text)""", video_script)
            time.sleep(0.3)

            # Paste the script - this triggers ProseMirror's paste handler
            page.keyboard.press(f"{modifier_key}+v")
            time.sleep(2)  # Give extra time for large scripts (20k+ words)
            paste_ok = True
        except Exception as e:
            print(f"⚠️ Clipboard paste failed: {e}")

        if not paste_ok and sys.platform != "darwin":
            try:
                page.keyboard.press("Shift+Insert")
                time.sleep(2)
                paste_ok = True
            except Exception as e:
                print(f"⚠️ Windows paste fallback failed: {e}")

        if not paste_ok:
            print("⌨️ Falling back to direct text insert...")
            page.keyboard.insert_text(video_script)
            time.sleep(2)
        
        print(f"✅ Script added ({len(video_script)} characters)")
        
        # Name the video with timestamp + scene folder name
        current_datetime = datetime.now().strftime("%m/%d/%Y %I:%M %p")
        video_name = f"{current_datetime} {scene_folder}"
        
        page.locator('//input[@placeholder="Untitled Video"]').fill(video_name)
        print(f"🏷️ Video named: '{video_name}'")
        
        # Select "Apollo" / Engine 4.0 - Unlimited option
        print("🔄 Checking Avatar Engine (Unlimited)...")
        try:
            # 1. Click the engine dropdown button (using user-provided selector)
            # The button usually shows "Avatar IV" or similar
            engine_dropdown = page.locator('button.hover\\:tw-bg-fill-blockHover:has(span.tw-text-textTitle:text-matches("Avatar", "i"))')
            
            # If the specific button selector from user is needed more precisely:
            if engine_dropdown.count() == 0:
                 # Fallback to broader selector if "Avatar IV" text changes (e.g. "Instant Avatar")
                 engine_dropdown = page.locator('button:has(img[alt*="Avatar"])')
            
            if engine_dropdown.count() > 0 and engine_dropdown.first.is_visible():
                engine_dropdown.first.click()
                time.sleep(1)
                
                # 2. Select "Unlimited" from the dropdown (using user-provided selector)
                # Look for the menu item containing "Unlimited" text and checkmark icon
                unlimited_option = page.locator('div[role="menuitem"]:has-text("Unlimited")')
                
                if unlimited_option.count() > 0:
                    # Check if it is already selected (it might have a visible checkmark or special class)
                    # The user's HTML shows a checkmark icon inside the div if selected
                    # <iconpark-icon class="iconpark-icon tw-text-more-grass" name="checkmark" ...>
                    
                    # We can click it anyway; usually clicking an already selected option does nothing or stays selected.
                    # But let's see if we can detect it.
                    
                    unlimited_option.first.click()
                    time.sleep(1)
                    print("✅ Selected 'Unlimited' engine")
                else:
                    print("ℹ️ 'Unlimited' option not found in dropdown")
                    # Click away to close dropdown
                    page.mouse.click(0, 0)
            else:
                 print("ℹ️ Engine dropdown not found, skipping...")
                 
        except Exception as e:
            print(f"⚠️ Could not select Avatar Unlimited: {e}")
        
        # Enable subtitles if requested
        if config["subtitles"] == "yes":
            print("📝 Enabling subtitles...")
            try:
                page.locator('button:has(iconpark-icon[name="cc-captions"])').click()
                time.sleep(1)
                page.locator('div.tw-grid.tw-gap-4.tw-pt-4.tw-grid-cols-1 button').first.click()
                time.sleep(1)
                print("✅ Subtitle template selected")
            except Exception as e:
                print(f"⚠️ Could not enable subtitles: {e}")
        
        # Click Generate
        print("⚙️ Clicking Generate...")
        self._dismiss_modal_overlays(page)
        self._dismiss_rating_popup(page)
        try:
            generate_button = page.locator('button:has-text("Generate")')
            
            # Check if button is disabled
            if generate_button.is_disabled():
                print("\n" + "="*60)
                print("❌ ERROR: Generate button is disabled!")
                print("="*60)
                print("\n⚠️ Possible reasons:")
                print("   • Avatar doesn't have any audio/script assigned")
                print("   • Script content is empty or invalid")
                print("   • Please add audio to the avatar and run the code again.")
                print("\n" + "="*60 + "\n")
                return False
            
            generate_button.click()
            page.wait_for_selector('text=Generate video', timeout=5000)
            time.sleep(2)
            print("✅ Generate modal opened")
        except Exception as gen_error:
            print("\n" + "="*60)
            print("❌ ERROR: Could not open Generate modal!")
            print("="*60)
            print(f"\n⚠️ Error: {gen_error}")
            print("\n⚠️ Possible reasons:")
            print("   • Avatar doesn't have any audio/script assigned")
            print("   • Script content is empty or invalid")
            print("   • Please add audio to the avatar and run the code again.")
            print("\n" + "="*60 + "\n")
            return False
        
        # Set Resolution
        print(f"🎥 Setting resolution to {config['quality']}...")
        page.locator('text=Resolution').locator('..').locator('button[role="combobox"]').click()
        time.sleep(1)
        
        if config['quality'] == "1080p":
            page.locator('[data-item-label="true"]:has-text("1080p")').click()
        else:
            page.locator('[data-item-label="true"]:has-text("720p")').click()
        time.sleep(1)
        
        # Set FPS
        print(f"🎥 Setting FPS to {config['fps']}...")
        page.locator('div.tw-flex.tw-flex-col.tw-gap-1:has-text("Fps") button[role="combobox"]').click()
        time.sleep(1)
        page.locator(f'[data-item-label="true"]:has-text("{config["fps"]}")').click()
        time.sleep(1)
        

        
        # Select folder (use the heygen_folder_name which includes date/time)
        print(f"📂 Selecting folder '{heygen_folder_name}'...")
        page.locator('div.tw-flex.tw-flex-col.tw-gap-1:has-text("Add to folder") button').click()
        time.sleep(2)
        
        try:
            page.locator(f'input[value="{heygen_folder_name}"]').locator('..').locator('..').locator('..').click()
            time.sleep(1)
        except:
            page.locator(f'div[data-folder-id]:has-text("{heygen_folder_name}")').first.click()
            time.sleep(1)
        
        page.locator('button:has-text("Confirm"):has(iconpark-icon[name="use"])').click()
        time.sleep(1)
        print(f"✅ Folder selected: '{heygen_folder_name}'")
        
        # Submit
        print("✅ Submitting video generation...")
        page.locator('//button[normalize-space()="Submit"]').click()
        
        # Wait for submission to complete
        print("⏳ Waiting for submission...")
        time.sleep(5)
        self._dismiss_modal_overlays(page)
        
        
        # Add to tracking
        self.add_video_to_project(tracking_data, project_name, scene_folder, script_filename + ".txt", video_name)
        self.save_tracking(tracking_data)
        
        print(f"📋 Tracking updated: {scene_folder}")
        return True
    
    def _navigate_to_project_folder(self, page, heygen_folder_name):
        """Navigate to a HeyGen project folder (shared helper)
        Returns: True on success, False on failure
        """
        print("📂 Navigating to project folder...")
        
        # First go to HeyGen homepage to reset state
        page.goto("https://www.heygen.com/")
        time.sleep(3)
        self._dismiss_rating_popup(page)
        
        # Click Projects menu
        page.locator('[data-testid="projects-menu"]').click()
        time.sleep(5)  # Wait longer for folders to load
        
        # Find and click the folder
        print(f"🔍 Looking for folder: {heygen_folder_name}")
        try:
            # Find folder by name in span (works with both folder icon and loading spinner)
            folder_element = page.locator(f'div[draggable="true"]:has(span.tw-text-textTitle:text-is("{heygen_folder_name}"))').first
            folder_element.dblclick()
            time.sleep(3)
            print(f"✅ Opened folder: {heygen_folder_name}")
            return True
        except Exception as e:
            print(f"❌ Could not find folder '{heygen_folder_name}'")
            print(f"   Error: {e}")
            print("   Please make sure the folder exists in HeyGen.")
            return False
    
    def _download_single_video(self, page, video, tracking_data):
        """Download a single completed video (shared helper)
        Returns: True on success, False on failure
        """
        try:
            print(f"   📥 Downloading: {video['scene_folder']}")
            
            # Find the video card
            video_cards = page.locator('div.tw-group:has(iconpark-icon[name="play"])').all()
            video_name_to_find = video["video_name"]
            
            target_video = None
            for card in video_cards:
                try:
                    card_text = card.inner_text()
                    if video_name_to_find in card_text:
                        target_video = card
                        print(f"   ✅ Found matching video: {video_name_to_find}")
                        break
                except:
                    pass
            
            if not target_video:
                print(f"   ⏳ {video['scene_folder']} not ready yet...")
                return False
            
            target_video.hover()
            time.sleep(1)
            
            three_dot_button = target_video.locator('button:has(iconpark-icon[name="more-level"])')
            three_dot_button.click()
            time.sleep(1)
            
            page.locator('div.tw-cursor-pointer.hover\\:tw-bg-ux-hover:has(iconpark-icon[name="download"]):has-text("Download")').click()
            time.sleep(2)
            
            page.locator('button:has(iconpark-icon[name="download"]):has-text("Download")').click()
            
            print("   ⏳ Waiting for download to complete...")
            latest_file = self.wait_for_latest_download(self.output_files_dir)
            
            if latest_file:
                file_extension = os.path.splitext(latest_file)[1] or ".mp4"
                safe_name = self._sanitize_filename(video["video_name"])
                new_filename = f"{safe_name}{file_extension}"
                new_path = os.path.join(self.output_files_dir, new_filename)
                
                if os.path.exists(new_path):
                    os.remove(new_path)
                
                os.rename(latest_file, new_path)
                
                self.update_video_status(tracking_data, video["scene_folder"], "downloaded", new_filename)
                self.save_tracking(tracking_data)
                
                print(f"   ✅ Downloaded: {new_filename}")
                return True
            else:
                print("   ❌ Download did not complete.")
                return False
                
        except Exception as e:
            print(f"   ❌ Error downloading: {e}")
            self.update_video_status(tracking_data, video["scene_folder"], "processing", error_message=str(e))
            self.save_tracking(tracking_data)
            return False
    
    def _poll_and_download_loop(self, page, tracking_data):
        """Long-running poll loop for completed video downloads."""
        
        start_time = time.time()
        cycle = 0
        
        print("\n⏳ Starting polling loop. No timeout; press Ctrl+C to stop.")
        
        while True:
            # Refresh tracking data from file (in case we want to support dynamic updates, 
            # though currently we just use the passed dict. Good practice to reload if passing file path)
            # tracking_data = self.load_tracking() # Optional if we moved to file-based state
            
            projects = tracking_data.get("projects", [])
            total_pending_all = 0
            projects_with_pending = []
            
            for project in projects:
                pending_count = sum(1 for v in project["videos"] if v["status"] == "processing")
                if pending_count > 0:
                    total_pending_all += pending_count
                    projects_with_pending.append(project)
            
            if total_pending_all == 0:
                print("\n🎉 All videos in all projects downloaded!")
                break
                
            cycle += 1
            print(f"\n🔄 Cycle {cycle}: {total_pending_all} videos pending across {len(projects_with_pending)} projects")
            print(f"   (Elapsed: {int((time.time()-start_time)/60)} min)")

            # Cycle through each project that has pending videos
            for project in projects_with_pending:
                folder_name = project['heygen_folder_name']
                print(f"\n   📂 Switching to folder: {folder_name}")
                
                # Navigate to the specific folder
                if not self._navigate_to_project_folder(page, folder_name):
                    print("      ❌ Could not open folder, skipping this cycle.")
                    continue
                
                # Check videos in this folder
                # We are now inside the folder, so we scan the video cards here
                try:
                    video_cards = page.locator('div.tw-group:has(iconpark-icon[name="play"])').all()
                    
                    pending_videos = [v for v in project["videos"] if v["status"] == "processing"]
                    for video in pending_videos:
                         self._download_if_ready(page, video, project, tracking_data, video_cards)
                         
                except Exception as e:
                    print(f"      ⚠️ Error checking folder: {e}")

            # Wait before next full cycle
            print(f"\n   💤 Waiting {POLLING_SLEEP_SECONDS}s before next cycle...")
            time.sleep(POLLING_SLEEP_SECONDS)

        return tracking_data

    def _download_if_ready(self, page, video, project, tracking_data, video_cards):
        """Try to download a specific video if it appears in video_cards"""
        video_name_to_find = video["video_name"]
        
        target_video = None
        for card in video_cards:
            try:
                if video_name_to_find in card.inner_text():
                    target_video = card
                    break
            except:
                pass
        
        if target_video:
            print(f"      ✅ Ready: {video['scene_folder']}")
            # Download logic (reused)
            try:
                target_video.hover()
                time.sleep(1)
                target_video.locator('button:has(iconpark-icon[name="more-level"])').click()
                time.sleep(1)
                page.locator('div.tw-cursor-pointer.hover\\:tw-bg-ux-hover:has(iconpark-icon[name="download"]):has-text("Download")').click()
                time.sleep(2)
                page.locator('button:has(iconpark-icon[name="download"]):has-text("Download")').click()
                
                latest_file = self.wait_for_latest_download(self.output_files_dir)
                if latest_file:
                     # Rename
                    file_extension = os.path.splitext(latest_file)[1] or ".mp4"
                    safe_name = self._sanitize_filename(video["video_name"])
                    new_filename = f"{safe_name}{file_extension}"
                    new_path = os.path.join(self.output_files_dir, new_filename)
                    if os.path.exists(new_path):
                         os.remove(new_path)
                    os.rename(latest_file, new_path)
                    
                    self.update_video_status(tracking_data, video["scene_folder"], "downloaded", new_filename)
                    self.save_tracking(tracking_data)
                    print(f"      📥 Downloaded: {new_filename}")
            except Exception as e:
                print(f"      ❌ Download error: {e}")
        else:
            # Not ready
            pass
    
    # ============================================
    # MODE 1: SUBMIT NEW VIDEOS
    # ============================================
    
    def run_submission_mode(self):
        """Batch submit all videos from selected project"""
        
        # Get project and scenes
        project_name, scene_list = self.get_project_info()
        
        # Get user preferences (once for all videos)
        config = self.get_user_preferences()
        
        # Create HeyGen folder name with date + time + project name
        folder_datetime = datetime.now().strftime("%m-%d-%Y %I-%M %p")
        heygen_folder_name = f"{folder_datetime} {project_name}"
        
        # Create tracking data
        tracking_data = self.create_new_tracking(project_name, heygen_folder_name, config)
        
        with sync_playwright() as p:
            context = self.launch_browser(p)
            if not context:
                return
            
            try:
                page = self._get_or_create_page(context)
                
                # Navigate to HeyGen
                print("🌐 Navigating to HeyGen...")
                page.goto("https://www.heygen.com/")
                time.sleep(3)
                
                print("\n" + "="*60)
                print("🚀 Starting Batch Submission Workflow")
                print("="*60 + "\n")
                
                # Create folder
                self._create_heygen_folder(page, heygen_folder_name)
                
                # Select avatar
                selected_avatar_idx, selected_avatar = self._select_avatar_interactive(page)
                if selected_avatar_idx is None:
                    return
                
                config["avatar_name"] = selected_avatar
                tracking_data["config"] = config
                
                # Process each scene
                total_scenes = len(scene_list)
                
                for scene_idx, (scene_folder, script_path, script_filename) in enumerate(scene_list, 1):
                    print("\n" + "="*60)
                    print(f"🎬 Processing Scene {scene_idx}/{total_scenes}: {scene_folder}")
                    print("="*60 + "\n")
                    
                    success = self._submit_single_video(
                        page, scene_folder, script_path, script_filename,
                        config, heygen_folder_name, selected_avatar_idx, tracking_data
                    )
                    
                    if not success:
                        return  # Stop on failure
                    
                    print(f"✅ Scene {scene_idx}/{total_scenes} submitted!")
                    
                    # Small delay before next submission
                    if scene_idx < total_scenes:
                        print("\n⏳ Waiting 5 seconds before next submission...")
                        time.sleep(5)
                
                # Submission complete
                print("\n" + "="*60)
                print("🎉 BATCH SUBMISSION COMPLETE!")
                print("="*60)
                print(f"\n📁 Project: {project_name}")
                print(f"📹 Videos submitted: {total_scenes}")
                print(f"📋 Tracking file: {self.tracking_file}")
                print(f"📂 HeyGen folder: {heygen_folder_name}")
                print("\n💡 Run the script again and select 'Option 2' to check and download videos.")
                print("   Videos should be ready in approximately 30 minutes.")
                print("\n" + "="*60 + "\n")
                
            except Exception as e:
                print(f"\n❌ Error during submission: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context.close()
                print("✅ Submission mode complete. Browser closed.")
    
    # ============================================
    # MODE 2: CHECK & DOWNLOAD PENDING VIDEOS
    # ============================================
    
    def run_download_mode(self):
        """Check and download pending videos"""
        
        # Load tracking data
        tracking_data = self.load_tracking()
        
        if not tracking_data:
            print("\n❌ No tracking data found!")
            print(f"   Looking for: {self.tracking_file}")
            print("   Please run 'Submit new videos' first.")
            return
        
        # Show summary
        project_name = tracking_data["project_name"]
        videos = tracking_data["videos"]
        
        downloaded = sum(1 for v in videos if v["status"] == "downloaded")
        pending = sum(1 for v in videos if v["status"] == "processing")
        
        print("\n" + "="*60)
        print("📥 CHECK & DOWNLOAD PENDING VIDEOS")
        print("="*60 + "\n")
        
        heygen_folder_name = tracking_data.get("heygen_folder_name", project_name)
        print(f"📁 Project: {project_name}")
        print(f"📊 Status: {downloaded}/{len(videos)} downloaded, {pending} pending")
        print(f"📂 HeyGen folder: {heygen_folder_name}")
        print("")
        
        if pending == 0:
            print("✅ All videos have been downloaded!")
            return
        
        # Show pending videos with time elapsed
        print("⏳ Pending videos:")
        now = datetime.now()
        min_time_remaining = float('inf')
        
        for video in videos:
            if video["status"] == "processing":
                submitted = datetime.fromisoformat(video["submitted_at"])
                elapsed = now - submitted
                elapsed_minutes = int(elapsed.total_seconds() / 60)
                time_remaining = max(0, 30 - elapsed_minutes)
                min_time_remaining = min(min_time_remaining, time_remaining)
                ready_marker = "✅ Ready to check" if elapsed_minutes >= 30 else f"⏳ {time_remaining} min until check"
                print(f"   • {video['scene_folder']} ({elapsed_minutes} min ago) - {ready_marker}")
        print("")
        
        # Ask user what to do
        if min_time_remaining > 0:
            print(f"⏰ Earliest video will be ready for check in {int(min_time_remaining)} minutes.")
            print("\nOptions:")
            print("  1. Wait for videos to finish (auto-poll every 90 seconds)")
            print("  2. Check now (skip videos not yet ready)")
            print("  3. Cancel")
            
    def run_submission_mode(self):
        """Batch submit new videos (Queue System - Submission Only)"""
        print("\n" + "="*60)
        print("� SUBMISSION MODE (Option 1)")
        print("="*60)

        # 0. Check for Existing Session to Append
        resume_mode = False
        existing_tracking = self.load_tracking()
        
        if existing_tracking and "projects" in existing_tracking and len(existing_tracking["projects"]) > 0:
            print("\n⚠️ Found existing tracking session from:", existing_tracking.get("session_start", "Unknown"))
            resume_choice = input("👉 Append to this session? (1. Yes / 2. Start New): ").strip()
            if resume_choice == "1":
                print("✅ Appending to existing session...")
                tracking_data = existing_tracking
                resume_mode = True
            else:
                print("🆕 Starting fresh session (old tracking.json overwritten)")
                tracking_data = self.create_new_tracking_session()
                self.save_tracking(tracking_data)
        else:
            tracking_data = self.create_new_tracking_session()
            self.save_tracking(tracking_data)

        # 1. Build the Queue
        job_queue = self.build_job_queue()
        if not job_queue:
            print("❌ No jobs queued.")
            return

        # Get user preferences (Quality/FPS) - Global
        config = self.get_user_preferences()
        
        with sync_playwright() as p:
            context = self.launch_browser(p)
            if not context:
                return
            
            try:
                page = self._get_or_create_page(context)
                
                print("🌐 Navigating to HeyGen...")
                page.goto("https://www.heygen.com/")
                time.sleep(3)
                
                job_count = len(job_queue)
                for job_idx, job in enumerate(job_queue, 1):
                    avatar_name = job["avatar"]
                    projects_data = job["projects"]
                    
                    print(f"\n🏭 Processing Job {job_idx}/{job_count}")
                    print(f"   👤 Avatar: {avatar_name}")
                    print(f"   � Projects: {[p[0] for p in projects_data]}")
                    
                    config["avatar_name"] = avatar_name
                    
                    for project_name, scene_list in projects_data:
                        print(f"\n   👉 Starting Project: {project_name}")
                        
                        # Create unique folder
                        folder_datetime = datetime.now().strftime("%m-%d-%Y %I-%M %p")
                        heygen_folder_name = f"{folder_datetime} {project_name}"
                        
                        # Add project to tracking
                        self.add_project_to_tracking(tracking_data, project_name, heygen_folder_name, config)
                        self.save_tracking(tracking_data)
                        
                        # Create Folder on HeyGen
                        self._create_heygen_folder(page, heygen_folder_name)
                        
                        # Process Scenes
                        total_scenes = len(scene_list)
                        for scene_idx, (scene_folder, script_path, script_filename) in enumerate(scene_list, 1):
                            print(f"\n   🎬 Submitting Scene {scene_idx}/{total_scenes}: {scene_folder}")
                            
                            success = self._submit_single_video(
                                page, scene_folder, script_path, script_filename,
                                config, heygen_folder_name, avatar_name, tracking_data, project_name
                            )
                            
                            if success:
                                print(f"   ✅ Scene submitted!")
                            else:
                                print(f"   ❌ Scene failed!")
                                
                            if scene_idx < total_scenes:
                                time.sleep(5)
                                
                    print(f"\n✅ Job {job_idx} Complete!")

                print("\n" + "="*60)
                print("✅ SUBMISSION PHASE COMPLETE")
                print("="*60)
                print("💡 Use Option 2 to check status and download videos later.")
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Stopped by user (Ctrl+C)")
            except Exception as e:
                print(f"\n❌ Error during submission: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context.close()
                print("✅ Browser closed.")
    

    def run_download_mode(self):
        """Check and download pending videos (Multi-Project)"""
        print("\n" + "="*60)
        print("📥 DOWNLOAD MODE (Option 2)")
        print("="*60)
        
        # Load tracking data
        tracking_data = self.load_tracking()
        
        if not tracking_data or "projects" not in tracking_data or not tracking_data["projects"]:
            print("\n❌ No valid tracking session found!")
            print(f"   Looking for: {self.tracking_file}")
            print("   Please run Option 1 or 3 first to create jobs.")
            return

        print(f"\n✅ Found tracking session started at: {tracking_data.get('session_start')}")
        print(f"   Monitoring {len(tracking_data['projects'])} projects.")

        with sync_playwright() as p:
            context = self.launch_browser(p)
            if not context:
                return
            
            try:
                page = self._get_or_create_page(context)
                
                print("🌐 Navigating to HeyGen...")
                page.goto("https://www.heygen.com/")
                time.sleep(3)
                
                # Check directly into polling loop
                self._poll_and_download_loop(page, tracking_data)

            except KeyboardInterrupt:
                print("\n\n⚠️ Stopped by user (Ctrl+C)")
            except Exception as e:
                print(f"\n❌ Error during download check: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context.close()
                print("✅ Browser closed.")

    # ============================================
    # MODE 3: UNATTENDED MODE (SUBMIT + DOWNLOAD)
    # ============================================
    
    
    def build_job_queue(self):
        """Interactive loop to build the job queue"""
        job_queue = []
        
        # Load avatars
        avatars = self.load_config()
        if not avatars:
            print("❌ No avatars found in config.txt. Please verify the file.")
            return []
            
        print("\n" + "="*60)
        print("🏭 JOB QUEUE BUILDER")
        print("="*60)
        
        while True:
            # 1. Select Projects
            selected_projects_data = self.get_project_info()
            if not selected_projects_data:
                break
                
            # 2. Select Avatar
            print("\n" + "="*60)
            print("👽 AVAILABLE AVATARS (from config.txt)")
            print("="*60)
            for idx, av in enumerate(avatars, 1):
                print(f"  {idx}. {av}")
                
            while True:
                try:
                    choice = int(input(f"\n👉 Select avatar to apply (1-{len(avatars)}): "))
                    if 1 <= choice <= len(avatars):
                        selected_avatar = avatars[choice-1]
                        print(f"✅ Selected Avatar: {selected_avatar}")
                        break
                    print("❌ Invalid selection")
                except:
                    print("❌ Invalid input")
            
            # Add to queue
            job_queue.append({
                "projects": selected_projects_data, # List of (project_name, scene_list)
                "avatar": selected_avatar
            })
            
            print(f"\n✅ Added to Queue. Current Jobs: {len(job_queue)}")
            
            # 3. Queue more?
            more = input("\n👉 Queue more projects? (1. Yes / 2. No): ").strip()
            if more != "1":
                break
                
        return job_queue

    def run_unattended_mode(self):
        """Submit all videos, then keep polling and downloading until all complete"""
        
        print("\n" + "="*60)
        print("🌙 UNATTENDED OVERNIGHT MODE (QUEUE SYSTEM)")
        print("="*60)
        
        # 0. Check for Resume
        resume_mode = False
        existing_tracking = self.load_tracking()
        
        if existing_tracking and "projects" in existing_tracking and len(existing_tracking["projects"]) > 0:
            print("\n⚠️ Found existing tracking session from:", existing_tracking.get("session_start", "Unknown"))
            resume_choice = input("👉 Resume this session? (1. Yes / 2. Start New): ").strip()
            if resume_choice == "1":
                print("✅ Resuming previous session...")
                tracking_data = existing_tracking
                resume_mode = True
            else:
                print("🆕 Starting fresh session (old tracking.json overwritten)")
                tracking_data = self.create_new_tracking_session()
                self.save_tracking(tracking_data)
        else:
            tracking_data = self.create_new_tracking_session()
            self.save_tracking(tracking_data)

        job_queue = []
        config = {}
        
        if not resume_mode:
            # 1. Build the Queue
            job_queue = self.build_job_queue()
            if not job_queue:
                print("❌ No jobs queued.")
                return
                
            # Get user preferences (Quality/FPS) - Global for all
            config = self.get_user_preferences()
        else:
             print("⏩ Skipping Queue Builder (Resume Mode)")
             config = {"quality": "720p", "fps": "25", "subtitles": "yes"} # Default filler
        
        with sync_playwright() as p:
            context = self.launch_browser(p)
            if not context:
                return
            
            try:
                page = self._get_or_create_page(context)
                
                # Navigate to HeyGen
                print("🌐 Navigating to HeyGen...")
                page.goto("https://www.heygen.com/")
                time.sleep(3)
                
                print("\n" + "="*60)
                print("📤 PHASE 1: PROCESS SUBMISSION QUEUE")
                print("="*60 + "\n")
                
                job_count = len(job_queue)
                for job_idx, job in enumerate(job_queue, 1):
                    avatar_name = job["avatar"]
                    projects_data = job["projects"]
                    
                    print(f"\n🏭 Processing Job {job_idx}/{job_count}")
                    print(f"   👤 Avatar: {avatar_name}")
                    print(f"   📂 Projects: {[p[0] for p in projects_data]}")
                    
                    config["avatar_name"] = avatar_name
                    
                    for project_name, scene_list in projects_data:
                        print(f"\n   👉 Starting Project: {project_name}")
                        
                        # Create unique folder
                        folder_datetime = datetime.now().strftime("%m-%d-%Y %I-%M %p")
                        heygen_folder_name = f"{folder_datetime} {project_name}"
                        
                        # Add project to tracking
                        self.add_project_to_tracking(tracking_data, project_name, heygen_folder_name, config)
                        self.save_tracking(tracking_data)
                        
                        # Create Folder on HeyGen
                        self._create_heygen_folder(page, heygen_folder_name)
                        
                        # Process Scenes
                        total_scenes = len(scene_list)
                        for scene_idx, (scene_folder, script_path, script_filename) in enumerate(scene_list, 1):
                            print(f"\n   🎬 Submitting Scene {scene_idx}/{total_scenes}: {scene_folder}")
                            
                            success = self._submit_single_video(
                                page, scene_folder, script_path, script_filename,
                                config, heygen_folder_name, avatar_name, tracking_data, project_name
                            )
                            
                            if success:
                                print(f"   ✅ Scene submitted!")
                            else:
                                print(f"   ❌ Scene failed!")
                                
                            if scene_idx < total_scenes:
                                time.sleep(5)
                                
                    print(f"\n✅ Job {job_idx} Complete!")
                
                # Phase 2: Poll and Download
                print("\n" + "="*60)
                print("📥 PHASE 2: WAITING & DOWNLOADING")
                print("="*60)
                
                tracking_data = self._poll_and_download_loop(page, tracking_data)
                
                print("\n🎉 WORKFLOW COMPLETE!")
                
            except KeyboardInterrupt:
                print("\n\n⚠️ Stopped by user (Ctrl+C)")
            except Exception as e:
                print(f"\n❌ Error during unattended mode: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context.close()
                print("✅ Browser closed.")

    def run_ui_queue(self, queue_path):
        """Submit videos from the web UI queue (no inputFiles needed)"""
        queue_data = self.load_ui_queue(queue_path)
        if not queue_data:
            print("❌ No UI queue data found.")
            return

        items = queue_data.get("items", [])
        avatar_name = (queue_data.get("avatar") or "").strip()
        project_name = (queue_data.get("project_name") or "Pasted Scripts").strip()
        config_in = queue_data.get("config", {})

        config = {
            "quality": config_in.get("quality", "720p"),
            "fps": config_in.get("fps", "25"),
            "subtitles": config_in.get("subtitles", "yes"),
            "avatar_name": avatar_name,
        }

        if not avatar_name:
            print("❌ Avatar name is required.")
            return
        valid_items = [item for item in items if str(item.get("script", "")).strip()]

        if not valid_items:
            print("❌ Queue is empty.")
            return

        folder_datetime = datetime.now().strftime("%m-%d-%Y %I-%M %p")
        heygen_folder_name = f"{folder_datetime} {project_name}"

        tracking_data = self.create_new_tracking_session()
        self.add_project_to_tracking(tracking_data, project_name, heygen_folder_name, config)
        self.save_tracking(tracking_data)

        with sync_playwright() as p:
            context = self.launch_browser(p)
            if not context:
                return

            try:
                page = self._get_or_create_page(context)

                print("🌐 Navigating to HeyGen...")
                page.goto("https://www.heygen.com/")
                time.sleep(3)

                print("\n" + "="*60)
                print("🚀 Starting UI Queue Submission")
                print("="*60 + "\n")

                self._create_heygen_folder(page, heygen_folder_name)

                total_items = len(valid_items)
                for idx, item in enumerate(valid_items, 1):
                    title = str(item.get("title", "")).strip()
                    if not title:
                        title = f"Untitled {idx}"

                    script_text = str(item.get("script", "")).strip()

                    script_filename = self._sanitize_filename(title)
                    if not script_filename:
                        script_filename = f"pasted_{idx}"

                    print("\n" + "="*60)
                    print(f"🎬 Processing {idx}/{total_items}: {title}")
                    print("="*60 + "\n")

                    success = self._submit_single_video(
                        page, title, None, script_filename,
                        config, heygen_folder_name, avatar_name, tracking_data, project_name,
                        script_text=script_text
                    )

                    if not success:
                        return

                    print(f"✅ Submitted: {title}")

                    if idx < total_items:
                        print("\n⏳ Waiting 5 seconds before next submission...")
                        time.sleep(5)

                print("\n" + "="*60)
                print("🎉 QUEUE SUBMISSION COMPLETE!")
                print("="*60)
                print(f"\n📁 Project: {project_name}")
                print(f"📹 Videos submitted: {total_items}")
                print(f"📋 Tracking file: {self.tracking_file}")
                print(f"📂 HeyGen folder: {heygen_folder_name}")
                print("\n📥 Auto-download enabled. Waiting for videos to finish...")
                print("   This will keep running until all videos download (Ctrl+C to stop).")
                print("\n" + "="*60 + "\n")

                print("\n" + "="*60)
                print("📥 PHASE 2: WAITING & DOWNLOADING")
                print("="*60)
                tracking_data = self._poll_and_download_loop(page, tracking_data)

                print("\n🎉 UI WORKFLOW COMPLETE!")

            except Exception as e:
                print(f"\n❌ Error during UI queue submission: {e}")
                import traceback
                traceback.print_exc()
            finally:
                context.close()
                print("✅ UI queue mode complete. Browser closed.")

    def run(self):
        """Main entry point with mode selection"""
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--ui-queue", dest="ui_queue", help="Path to UI queue JSON")
        args, _ = parser.parse_known_args()
        
        if args.ui_queue:
            self.run_ui_queue(args.ui_queue)
            return
        
        mode = self.get_mode_selection()
        
        if mode == "submit":
            self.run_submission_mode()
        elif mode == "download":
            self.run_download_mode()
        elif mode == "unattended":
            self.run_unattended_mode()

if __name__ == "__main__":
    automation = HeyGenAutomation()
    automation.run()

