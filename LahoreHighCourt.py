import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException


# Global variables to track progress
current_row = 2  # Start row
total_rows = 4034  # Adjust based on your case count

# Check internet connectivity
def check_internet(url='http://www.google.com', timeout=5, interval=10):
    while True:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                print("Internet is connected.")
                return
        except requests.ConnectionError:
            print(f"Connection failed. Retrying in {interval} seconds...")
        time.sleep(interval)


# Function to click on the 'Submit' button on the homepage
def click_on_submit(driver):
    try:
        submit_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="appjudgmentbtn"]'))
        )
        submit_button.click()
        print("Clicked on 'Submit' button.")
        time.sleep(35)  # Allow time for the page to load
    except Exception as e:
        print("Error clicking 'Submit' button:", e)


# Function to initialize the Selenium WebDriver
def initialize_driver(download_directory):
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(download_directory),
        "download.prompt_for_download": False,
        "directory_upgrade": True,
    })
    
    driver = webdriver.Firefox()
    return driver


# Function to download a file
def download_file(url, file_path):
    try:
        if not url:
            print("No URL provided for downloading.")
            return

        counter = 1
        base_path, ext = os.path.splitext(file_path)
        while os.path.exists(file_path):  # Ensure a unique filename
            file_path = f"{base_path}_{counter}{ext}"
            counter += 1

        response = requests.get(url)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"File downloaded successfully: {file_path}")
        else:
            print(f"Failed to download file, status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")


# Function to save data to JSON incrementally
def save_to_json_incremental(data, filename):
    try:
        # Try reading the existing data if the file exists
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    existing_data.append(data)  # Append to the list if it's a list
                    data = existing_data  # Update data with the new list
                else:
                    print("Existing JSON is not a list. Overwriting it.")
                    data = [data]  # If existing data is not a list, start a new list
        else:
            print(f"{filename} does not exist. A new file will be created.")
            data = [data]  # Start with a list if the file doesn't exist

    except (json.JSONDecodeError, FileNotFoundError) as e:
        # Handle cases where the file is not found or the JSON is invalid
        print(f"Error reading {filename}: {e}")
        data = [data]  # Start with a new list if there's an issue

    # Write the updated data back to the JSON file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Data appended to {filename}")



# Function to scrape case data
def scrape_case_data(driver, download_directory, json_filename):
    global current_row  # Use the global row tracker
    while current_row < total_rows:
        try:
            print(f"Scraping row {current_row}...")

            # Extract case details
            case_title = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[3]').text
            case_no = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[2]').text
            author_judge = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[4]').text
            judgment_date = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[5]').text
            sc_citation = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[6]').text
            court_type = "Lahore High Court"

            time.sleep(2)
            # Extract download link
            download_link_element = driver.find_element(By.XPATH, f'//*[@id="appjudgment"]/table[{current_row}]/tbody/tr[1]/td[8]/a')
            download_url = download_link_element.get_attribute("href")
            filename = os.path.basename(download_url)  # Use original file name from URL
            file_path = os.path.join(download_directory, filename)

            # Download file
            download_file(download_url, file_path)

            # Save case details
            case_details = {
                "caseNo": case_no,
                "caseTitle": case_title,
                "authorJudge": author_judge,
                "judgmentDate": judgment_date,
                "caseCitation": sc_citation,
                "courtType": court_type,
                "URL": download_url,
                "caseFile": os.path.basename(file_path),
            }

            # Save data incrementally to JSON
            save_to_json_incremental(case_details, json_filename)

            current_row += 1  # Move to the next row

        except NoSuchElementException as e:
            print(f"Error scraping row {current_row}: Element not found. Skipping...")
            current_row += 1  # Skip to the next row

        except WebDriverException as e:
            print(f"Error scraping row {current_row}: WebDriver issue. Restarting browser...")
            driver.quit()
            driver = initialize_driver(download_directory)
            driver.get('https://data.lhc.gov.pk/reported_judgments/judgments_approved_for_reporting')
            time.sleep(10)  # Allow page to load fully
            continue  # Retry the current row

        except Exception as e:
            print(f"Error scraping row {current_row}: {e}")
            current_row += 1  # Skip to the next row


# Main function to execute scraping
def main():
    global current_row
    check_internet()
    driver = initialize_driver("LahoreJudgements")
    try:
        driver.get('http://data.lhc.gov.pk/reported_judgments/judgments_approved_for_reporting')
        time.sleep(10)  # Wait for the page to load fully
        click_on_submit(driver)
        scrape_case_data(driver, "LahoreJudgements", "LahoreHighCourt.json")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
