from selenium import webdriver
from multiprocessing import Pool
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import DesiredCapabilities
import argparse, mail, os, re, time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import boto3
import smtplib

HOME = os.getenv("HOME")
AMZ = os.path.join(HOME, 'devel', 'amz')
RESULTS_FILE = os.path.join(AMZ, "results.txt")
ITEMS_FILE = os.path.join(AMZ, "items.txt")

def wait_for_any_element_to_display(driver, selector, timeout=3, step=.05):
    """ wait for any of multiple elements to be visible on page """
    try:
        return WebDriverWait(driver, timeout, step).until(
            EC.visibility_of_any_elements_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        raise NoSuchElementException(selector)

def wait_for_element_to_display(driver, selector, timeout=3, step=.05):
    """wait for element to be visible on page"""
    try:
        WebDriverWait(driver, timeout, step).until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
    except TimeoutException:
        raise NoSuchElementException(selector)

def select(driver, selector, wait_for_elem_to_be_visible=True, multiples=False):
        """select elements(s) from a page by css selector"""
        try:
            if wait_for_elem_to_be_visible:
                if multiples:
                    wait_for_any_element_to_display(driver, selector, timeout=3)
                else:
                    wait_for_element_to_display(driver, selector, timeout=3)
            if multiples:
                element = driver.find_elements_by_css_selector(selector)
            else:
                element = driver.find_element_by_css_selector(selector)

        except TimeoutException:
            raise NoSuchElementException()

        return element

def check_item(data):
    item_url = data[0]
    browser = data[1]
    try:
        if browser == "chrome":
            driver=webdriver.Chrome()
        elif browser == "chrome-headless":
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            driver = webdriver.Chrome(chrome_options=chrome_options)

        driver.get("https://www.amazon.com/")
        driver.get(item_url)
        select(driver, ".a-box-group #add-to-cart-button").click()
        driver.get("https://www.amazon.com/gp/cart/view.html?ref=nav_cart")
        item_title = select(driver, ".sc-product-title").text
        elem = select(driver, "span[data-a-class='quantity']")
        elem.click()
        select(driver, ".quantity-option-10").click()
        qinput = select(driver, "input[name='quantityBox'][style='display: inline-block;']")
        qinput.send_keys(999)
        select(driver, "a[data-action='update']").click()
        try:
            divider = "---------------------------------------------------------------------------------"
            msg = select(driver, "#activeCartViewForm .a-alert-content").text
            output = "ITEM: %s \nAMZ MSG: %s \n%s\n" %(item_title, msg, divider)
            print output
            write_results(output)
        except NoSuchElementException:
            output = "ITEM: %s \nMARK MSG: This item has more than 999 in stock. No amazon message. \n%s\n" %(item_title,divider)
            print output
            write_results(output)
        driver.quit()

    except Exception:
        if len(driver.window_handles) != 0:
            driver.quit()
        raise

def write_results(output):
    with open(RESULTS_FILE, "a") as f:
        f.write(output)

def delete_results():
    try: 
        os.remove(RESULTS_FILE)
    except Exception:
        pass

def email_results():

    date_time = datetime.now().strftime("%B %d, %Y %H:%M")
    COMMASPACE = ', '
    me = "markpang1@gmail.com" 
    my_password = "Brown123" 
    you = "markpang1@gmail.com"
    msg = MIMEMultipart()
    msg['Subject'] = "AMZ Results for %s" %date_time
    msg['From'] = me
    msg['To'] = COMMASPACE.join([you])
    part = MIMEApplication(open(RESULTS_FILE, "rb").read())
    part.add_header('Content-Disposition', 'attachment', filename="results.txt")
    msg.attach(part)
    s = smtplib.SMTP_SSL('smtp.gmail.com') 
    s.login(me, my_password)
    s.sendmail(me, you, msg.as_string())
    s.quit()

def main(browser, processes):
    delete_results()
    p = Pool(int(processes))
    with open(ITEMS_FILE) as f:
        items_url = f.readlines()
    list_items = []
    for item_url in items_url:
        list_items.append((item_url, browser))
    p.map(check_item, list_items)
    email_results()
    # list_items = ('https://www.amazon.com/Premium-Plastic-Plates-Alpha-Sigma/dp/B01MSOOPPL/ref=pd_rhf_sc_s_cp_0_3?_encoding=UTF8&pd_rd_i=B01MSOOPPL&pd_rd_r=WVJVA6Z5PJ87XRDCGRZ8&pd_rd_w=iDo7q&pd_rd_wg=Ase0d&psc=1&refRID=WVJVA6Z5PJ87XRDCGRZ8\n', 'chrome-headless')
    #check_item(list_items)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-b','--browser', default="chrome-headless", help="browser type")
    ap.add_argument('-p','--processes', default=10, help="browser type")
    args = vars(ap.parse_args())

    main(**args)