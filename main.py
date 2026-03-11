import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time




# ===== LOGIN INFO =====
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

email = config["linkedin"]["email"]
password = config["linkedin"]["password"]

keyword = config["job_search"]["keyword"]
location = config["job_search"]["location"]
MAX_PAGES = config["job_search"]["max_pages"]

excel_file = config["output"]["excel_file"]


driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)

# ===== LOGIN =====
driver.get("https://www.linkedin.com/login")
time.sleep(2)
driver.find_element(By.ID, "username").send_keys(email)
driver.find_element(By.ID, "password").send_keys(password)
driver.find_element(By.ID, "password").send_keys(Keys.RETURN)
time.sleep(5)

# ===== BUILD SEARCH URL =====
search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}"
driver.get(search_url)
time.sleep(5)

all_jobs = {}

def scrape_current_page():
    """Scroll job list container để load hết tất cả job cards trên trang hiện tại"""
    try:
        # Tìm container scroll của danh sách job (không phải body)
        job_list_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".jobs-search-results-list"))
        )
    except:
        job_list_container = None

    # Scroll từng bước nhỏ trong container để trigger occlusion load
    for step in range(20):
        if job_list_container:
            driver.execute_script(
                "arguments[0].scrollTop += 400;", job_list_container
            )
        else:
            driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(0.4)

    # Scroll lên đầu rồi xuống cuối để đảm bảo tất cả đã render
    if job_list_container:
        driver.execute_script("arguments[0].scrollTop = 0;", job_list_container)
        time.sleep(1)
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight;", job_list_container
        )
        time.sleep(2)

    # Lấy tất cả li có data-occludable-job-id
    job_items = driver.find_elements(By.CSS_SELECTOR, "li[data-occludable-job-id]")
    print(f"  → Tìm thấy {len(job_items)} job items trên trang này")

    for item in job_items:
        job_id = item.get_attribute("data-occludable-job-id")
        if job_id in all_jobs:
            continue
        try:
            # Scroll item vào viewport để nó render nội dung
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
            time.sleep(0.2)

            title = item.find_element(By.CSS_SELECTOR, "a.job-card-container__link").get_attribute("aria-label")
            company = item.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__subtitle span").text.strip()
            
            try:
                location_el = item.find_element(By.CSS_SELECTOR, ".artdeco-entity-lockup__caption span[dir='ltr']")
                loc = location_el.text.strip()
            except:
                loc = "N/A"

            link = f"https://www.linkedin.com/jobs/view/{job_id}"

            all_jobs[job_id] = {
                "title": title,
                "company": company,
                "location": loc,
                "link": link
            }
        except Exception as e:
            # Job chưa render nội dung, bỏ qua
            pass

# ===== SCRAPE NHIỀU TRANG =====
MAX_PAGES = 5  # Đổi số trang muốn lấy

for page_num in range(1, MAX_PAGES + 1):
    print(f"\n===== TRANG {page_num} =====")
    scrape_current_page()

    # Bấm nút "Next" để sang trang tiếp
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='View next page']")
        if next_btn.is_enabled():
            next_btn.click()
            time.sleep(4)
        else:
            print("Hết trang!")
            break
    except:
        print("Không tìm thấy nút Next.")
        break

# ===== IN KẾT QUẢ =====
print(f"\n\nTổng cộng: {len(all_jobs)} jobs")
print("=" * 50)
for job_id, info in all_jobs.items():
    print(f"ID     : {job_id}")
    print(f"Job    : {info['title']}")
    print(f"Công ty: {info['company']}")
    print(f"Địa điểm: {info['location']}")
    print(f"Link   : {info['link']}")
    print("-" * 40)

# ===== EXPORT TO EXCEL =====
data = []

for job_id, info in all_jobs.items():
    data.append({
        "Job ID": job_id,
        "Title": info["title"],
        "Company": info["company"],
        "Location": info["location"],
        "Link": info["link"]
    })

df = pd.DataFrame(data)

file_name = "linkedin_jobs.xlsx"
df.to_excel(file_name, index=False)

print(f"\nĐã lưu file Excel: {file_name}")


input("\nPress ENTER to close browser...")
driver.quit()