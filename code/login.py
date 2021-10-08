import os
import time
import urllib.request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract


def start_driver():
    """
    This function start  driver with relevent settings
    :return:
    """
    SELENIUM_DRIVER_PATH = os.path.normpath(os.getcwd() + os.sep + os.pardir) + "/chrome_driver/chromedriver_linux"
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1420,1080')

    driver = webdriver.Chrome(SELENIUM_DRIVER_PATH,
                              # chrome_options=chrome_options,
                              # desired_capabilities=DesiredCapabilities.CHROME
                              )
    # driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)
    return driver


def login(driver, username, passwrd):
    driver.get("http://www.mca.gov.in/mcafoportal/login.do")
    time.sleep(2)
    user_name = driver.find_element_by_xpath('//input[@name="userName"]')
    time.sleep(3)
    user_name.send_keys(username)
    time.sleep(3)
    password = driver.find_element_by_xpath('//input[@name="password"]')
    time.sleep(3)
    password.send_keys(passwrd)
    time.sleep(3)
    captcha_text = get_captcha(driver)
    captcha = driver.find_element_by_xpath('//input[@name="userEnteredCaptcha"]')
    captcha.send_keys(captcha_text)
    driver.find_element_by_xpath("//input[@value='Sign In']").click()
    time.sleep(5)
    check_captcha_error(driver)


def check_exists_by_xpath(driver, xpath):
    """
    This function check if xpath exist
    :param driver:
    :param xpath:
    :return:
    """
    try:
        driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return False
    return True


def check_captcha_error(driver):
    exist = check_exists_by_xpath(driver, "//p[@class='error']")
    if exist:
        driver.find_element_by_xpath(xpath).click()
        time.sleep(3)
        login(driver, username='jithin94', passwrd='Pass12#$')


def logout(driver):
    driver.find_element_by_xpath("//input[@id='loginAnchor']").click()
    time.sleep(5)


def get_captcha(driver):
    driver.find_element_by_xpath("//a[@id='captchaRefresh']").click()
    time.sleep(3)
    with open('captcha.png', 'wb') as file:
        file.write(driver.find_element_by_xpath('//img[@id="captcha"]').screenshot_as_png)
    # download the image
    text = pytesseract.image_to_string(Image.open("captcha.png"))
    return text


driver = start_driver()
login(driver, username='jithin94', passwrd='Pass12#$')
driver.quit()
