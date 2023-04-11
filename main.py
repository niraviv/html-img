import sys
import os
import random
import gzip
import requests
from bs4 import BeautifulSoup
from warcio.archiveiterator import ArchiveIterator
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Change TARGET_URL to None to choose randomly from Common Crawl:
TARGET_URL = 'https://yoshuabengio.org/'
CRAWL = 'CC-MAIN-2023-14'
CRAWL_DATA_BASE_PATH = 'crawl_data'
CRAWL_DATA_PATH = os.path.join(CRAWL_DATA_BASE_PATH, CRAWL)
OUTPUT_PATH = 'screenshots'

random.seed(42)


def create_dirs():
    for dir_path in [CRAWL_DATA_BASE_PATH, CRAWL_DATA_PATH, OUTPUT_PATH]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)


def download_warc_paths_file():
    warc_paths_file_name = os.path.join(CRAWL_DATA_PATH, 'warc_paths.txt')
    if not os.path.isfile(warc_paths_file_name):
        print('WARC paths file not present. Downloading.')
        warc_paths_url = f'https://data.commoncrawl.org/crawl-data/{CRAWL}/warc.paths.gz'
        response = requests.get(warc_paths_url)
        response.raise_for_status()
        index_file_content = gzip.decompress(response.content).decode('utf-8')
        with open(warc_paths_file_name, 'w') as f:
            f.write(index_file_content)
    print('WARC paths file present.')
    return warc_paths_file_name


def download_random_warc_file(warc_paths_file_name):
    warc_file_name = os.path.join(CRAWL_DATA_PATH, 'warc.gz')
    if not os.path.isfile(warc_file_name):
        with open(warc_paths_file_name, 'r') as f:
            warc_paths = f.readlines()
        rand_warc_path = random.choice(warc_paths).strip()
        rand_warc_url = f'https://data.commoncrawl.org/{rand_warc_path}'
        print(f'WARC file not present. Downloading random WARC URL:')
        print(rand_warc_url)
        response = requests.get(rand_warc_url)
        response.raise_for_status()
        with open(warc_file_name, 'wb') as f:
            f.write(response.content)
    print('WARC file present.')
    return warc_file_name


def is_valid_record(r):
    return r.rec_type == 'response' and r.http_headers.get_header('Content-Type') == 'text/html'


def get_random_record_from_warc_file(warc_file_name):
    with open(warc_file_name, 'rb') as f:
        arc_iter = ArchiveIterator(f)
        records = [r for r in arc_iter if is_valid_record(r)]

    return random.choice(records)


def get_screenshots_from_url(url):
    print('Continuing will send requests to the following URL:')
    print(url)
    if input(f'Are you sure? (y/n)').lower() != 'y':
        sys.exit(0)
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    driver = webdriver.Chrome(ChromeDriverManager().install())  # Note that this will install Chrome driver manager.
    actions = ActionChains(driver)

    # Set the window size to avoid cutting off the elements
    driver.set_window_size(1920, 1080)

    driver.get(url)

    # Wait for the page to fully load
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'body')))

    # Find all text-containing elements and take screenshots
    text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'li', 'span', 'button'])
    for i, element in enumerate(text_elements):
        try:
            xpath = '//' + element.name + '[text()="' + element.text.replace('"', '\\"') + '"]'
            screen_element = driver.find_element_by_xpath(xpath)

            # To take a screenshot of the specific element only:
            screen_element.screenshot(os.path.join(OUTPUT_PATH, f'{i}_element_only.png'))

            # To take a screenshot of the entire screen:
            actions.move_to_element(screen_element).perform()
            driver.save_screenshot(os.path.join(OUTPUT_PATH, f'{i}_full_screen.png'))

            # To save the element code:
            with open(os.path.join(OUTPUT_PATH, f'{i}.txt'), 'w') as f:
                f.write(str(element))
        except Exception as e:
            print(f"Error capturing screenshot for element {i}: {e}")

    driver.quit()


def main():
    create_dirs()
    url = TARGET_URL
    if not url:
        warc_paths = download_warc_paths_file()
        warc_file_name = download_random_warc_file(warc_paths)
        record = get_random_record_from_warc_file(warc_file_name)
        url = record.rec_headers['WARC-Target-URI']
    get_screenshots_from_url(url)
    print('Done.')


if __name__ == "__main__":
    main()
