import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException, \
    MoveTargetOutOfBoundsException
from webdriver_manager.chrome import ChromeDriverManager


def save_text_elements_and_screenshots(url):
    # Get website content
    response = requests.get(url)
    if response.status_code != 200:
        print("Error: Unable to access the website.")
        return

    # Parse website content and extract text elements
    soup = BeautifulSoup(response.content, "html.parser")
    text_elements = [element for element in soup.find_all(string=True) if
                     element.parent.name not in ['script', 'style', 'meta', 'link', 'noscript']]

    # Filter out text elements containing only whitespace
    text_elements = [element for element in text_elements if element.strip()]

    # Create a directory to save screenshots
    screenshot_dir = "screenshots"
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)

    # Initialize webdriver (automatically managed by webdriver-manager)
    driver = webdriver.Chrome(ChromeDriverManager().install())

    # Set the window size to a common resolution
    driver.set_window_size(1366, 768)

    # Open the website in the webdriver
    driver.get(url)

    # Create a dictionary to store the mapping between index and text element
    index_text_mapping = {}
    screenshot_index = 0

    # Keep track of the previous element's location to detect duplicates
    prev_element_location = None

    # Iterate through the text elements, hover over each one, and take a screenshot
    for index, element in enumerate(text_elements):
        try:
            # Get the selenium WebElement from the BeautifulSoup element
            xpath = f"//*[text()[contains(., {repr(element.strip())})]]"
            selenium_element = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))

            # Check if the element is interactable (has size and location)
            if selenium_element.size["height"] == 0 or selenium_element.size["width"] == 0:
                raise ElementNotInteractableException("Element not interactable")

            # Check if the current element's location is the same as the previous element's location
            current_element_location = selenium_element.location
            if prev_element_location and current_element_location == prev_element_location:
                continue  # Skip duplicates with the same position on the page

            # Scroll the element into view
            driver.execute_script("arguments[0].scrollIntoView();", selenium_element)

            # Move cursor to the element
            actions = ActionChains(driver)
            actions.move_to_element(selenium_element).perform()

            # Add the mapping to the dictionary
            index_text_mapping[screenshot_index] = element.strip()

            # Save the mapping to disk
            with open("index_text_mapping.json", "w", encoding='utf-8') as f:
                json.dump(index_text_mapping, f, ensure_ascii=False, indent=4)

            # Save the screenshot after updating the mapping
            driver.save_screenshot(os.path.join(screenshot_dir, f"screenshot_{screenshot_index}.png"))

            # Increment the screenshot index
            screenshot_index += 1

            # Update the previous element's location
            prev_element_location = current_element_location

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Error processing element {index}: {type(e).__name__} - {str(e)}")
        except (ElementNotInteractableException, MoveTargetOutOfBoundsException) as e:
            print(f"Error processing element {index}: {type(e).__name__} - {str(e)}")

    # Close the webdriver
    driver.quit()


if __name__ == "__main__":
    url = input("Enter the website URL: ")
    save_text_elements_and_screenshots(url)
