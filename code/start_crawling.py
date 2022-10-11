import zipfile
import time
import requests
import json
import random
import os
import datetime
import logging
from lxml import html

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

PROXY_HOST = 'us-wa.proxymesh.com'  # rotating proxy
PROXY_PORT = 31280
PROXY_USER = 'sourabh.phpdev'
PROXY_PASS = 'kittushalu'

CPANEL_IP = 'http://65.0.174.238'
manifest_json = """
{
    "version": "1.0.0",
    "manifest_version": 2,
    "name": "Chrome Proxy",
    "permissions": [
        "proxy",
        "tabs",
        "unlimitedStorage",
        "storage",
        "<all_urls>",
        "webRequest",
        "webRequestBlocking"
    ],
    "background": {
        "scripts": ["background.js"]
    },
    "minimum_chrome_version":"22.0.0"
}
"""

background_js = """
var config = {
        mode: "fixed_servers",
        rules: {
          singleProxy: {
            scheme: "http",
            host: "%s",
            port: parseInt(%s)
          },
          bypassList: ["localhost"]
        }
      };

chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

function callbackFn(details) {
    return {
        authCredentials: {
            username: "%s",
            password: "%s"
        }
    };
}

chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {urls: ["<all_urls>"]},
            ['blocking']
);
""" % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)


def get_proxy_list_service():
    """
    This return free proxy ip
    :return:
    """
    r = requests.get("https://api.getproxylist.com/proxy?country[]=IN&anonymity[]=high%20anonymity")
    PROXY = None
    if r.status_code == 200:
        respose = json.loads(r.text)
        PROXY = str(respose.get("ip")) + ":" + str(respose.get("port"))
        return PROXY


def check_if_ip_blocked(page_source):
    """
    This check if the ip is blocked or not
    :param page_source:
    :return:
    """
    doc = html.fromstring(page_source)
    title = doc.xpath("//title/text()")
    text = '404 Forbidden'
    if title:
        if text in title[0]:
            return True
    return False


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


def start_driver():
    """
    This function start  driver with relevent settings
    :return:
    """
    SELENIUM_DRIVER_PATH = os.path.normpath(os.getcwd() + os.sep + os.pardir) + "/chrome_driver/chromedriver_linux"
    chrome_options = Options()
    chrome_options.add_argument('--window-size=1420,1080')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    #chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(SELENIUM_DRIVER_PATH,chrome_options=chrome_options)
    logging.info("Chrome driver initalized")
    return driver


def get_all_cin():
    """
    This function get all CIN in database.
    :return:
    """
    cin_list = requests.get(url=CPANEL_IP + '/api/mca_info/cinList')
    cin_list = json.loads(cin_list.json())
    cin = []
    for  i in cin_list:
       cin.append(i.get("company_cin"))
    return cin


def searching_cin(count, driver, cin, data_push):
    """
    This function search for cin in MCA website
    :param driver:
    :param cin:
    :param data_push:
    :return:
    """
    main_url = 'https://www.mca.gov.in/mcafoportal/viewPublicDocumentsFilter.do'
    logging.info(str(count) + ") Processing CIN:" + str(cin))
    driver.get(main_url)
    if check_if_ip_blocked(driver.page_source):
        raise Exception('Ip Blocked')
    time.sleep(random.randint(8, 12))
    ckecks = driver.find_element_by_xpath('//input[@id="cinChk"]')
    ckecks.click()
    time.sleep(random.randint(0, 2))
    cin_input = driver.find_element_by_xpath('//input[@id="cinFDetails"]')
    time.sleep(random.randint(0, 2))
    cin_input.send_keys(cin)
    time.sleep(random.randint(3, 8))
    driver.find_element_by_xpath('//input[@id="viewDocuments_0"]').click()
    time.sleep(random.randint(0, 9))
    if check_exists_by_xpath(driver, '//a[@class="dashboardlinks"]'):
        go_to_detailed_page(cin, driver, data_push)
    else:
        logging.info("No details found")


def process_text(text):
    """
    This function cleans the text.
    :param text:
    :return:
    """
    if type(text) == list:
        text = text[0]
    text = text.replace("\n", "")
    text = text.replace("\t", "")
    return text


def get_year():
    """
    This function return current year
    :return:
    """
    return str(datetime.datetime.now().year)


def close_popup(driver):
    """
    This function close the pop up.
    :param driver:
    :return:
    """
    if check_exists_by_xpath(driver, '//a[@id="msgboxclose"]'):
        driver.find_element_by_xpath('//a[@id="msgboxclose"]').click()


def get_annual_finance(driver):
    """
    This function return current year annual finance data.
    :param driver:
    :return:
    """
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath(
        "//select[@name='categoryName']/option[text()='Annual Returns and Balance Sheet eForms']").click()
    time.sleep(random.randint(1, 3))
    xpath_str = "//select[@name='finacialYear']/option[text()='" + get_year() + "']"
    driver.find_element_by_xpath(xpath_str).click()
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath("//input[@id='viewCategoryDetails_0']").click()
    time.sleep(random.randint(0, 9))
    finance_response, finance_doc_status = parse_doc(driver)
    return finance_response, finance_doc_status


def get_eform(driver):
    """
    This function return current year eform data.
    :param driver:
    :return:
    """
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath("//select[@name='categoryName']/option[text()='Other eForm Documents']").click()
    time.sleep(random.randint(1, 3))
    xpath_str = "//select[@name='finacialYear']/option[text()='" + get_year() + "']"
    driver.find_element_by_xpath(xpath_str).click()
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath("//input[@id='viewCategoryDetails_0']").click()
    time.sleep(random.randint(0, 9))
    eform_response, eform_doc_status = parse_doc(driver)
    return eform_response, eform_doc_status


def get_other_attachments(driver):
    """
    This function return current year other attachments data.
    :param driver:
    :return:
    """
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath("//select[@name='categoryName']/option[text()='Other Attachments']").click()
    time.sleep(random.randint(1, 3))
    xpath_str = "//select[@name='finacialYear']/option[text()='" + get_year() + "']"
    driver.find_element_by_xpath(xpath_str).click()
    time.sleep(random.randint(1, 3))
    driver.find_element_by_xpath("//input[@id='viewCategoryDetails_0']").click()
    time.sleep(random.randint(0, 9))
    other_attachments_response, other_attachments_a_doc_status = parse_doc(driver)
    return other_attachments_response, other_attachments_a_doc_status


def parse_doc(driver):
    """
    This function parse table data .
    :param driver:
    :return:
    """
    try:
        doc = html.fromstring(driver.page_source)
        rows = doc.xpath("//table[@id='results']/tbody/tr/td")
        if not rows:
            close_popup(driver)
            return 'No documents are available for the selected category', False
        row_count = 0
        respose = ""
        for row in rows:
            text = row.xpath('./text()')
            respose = respose + process_text(text) + " :"
            row_count = row_count + 1
            if row_count % 2 == 0:
                respose = respose[:-1]
                respose = respose + "<br>"
        return respose, True
    except Exception as e:
        logging.info("Exception in Fetching Data:" + str(e))
    close_popup(driver)
    return 'No documents are available for the selected category', False


def save_to_api(cin, data):
    """
    This function save the crawled data to database
    :param cin:
    :param data:
    :return:
    """
    url = CPANEL_IP + "/api/mca_info/cinMarked/"
    payload = "cinNumer=" + cin + "&doc_present=" + str(data.get("finance").get("present")) + "&doc_information=" + str(
        data.get("finance").get("response")) + \
              "&other_eform_documents_present=" + str(
        data.get("eform").get("present")) + "&other_eform_documents_information=" + str(
        data.get("eform").get("response"))
    #       + \
    #       "&other_attachment_documents_present=" + str(
    # data.get("attachments").get("present")) + "&other_attachment_documents_information=" + str(
    # data.get("attachments").get("response"))

    headers = {
        'content-type': "application/x-www-form-urlencoded",
    }
    r = requests.post(url, data=payload, headers=headers)
    if r.status_code == 200:
        logging.info("Data Pushed to API CIN:" + str(cin))
    else:
        print("ERROR:", r.text)


def go_to_detailed_page(cin, driver, data_push):
    """
    This function go to the detailed page.
    :param cin:
    :param driver:
    :param data_push:
    :return:
    """
    logging.info("Search Sucessful redriecting to dashboard ....")
    driver.find_element_by_xpath('//a[@class="dashboardlinks"]').click()
    if check_if_ip_blocked(driver.page_source):
        raise Exception('Ip Blocked')
    time.sleep(random.randint(0, 9))
    logging.info("Fetching Finance Data ... ")
    finance_response, finance_doc_status = get_annual_finance(driver)
    logging.info("Fetching Eform Data ... ")
    eform_response, eform_doc_status = get_eform(driver)
    logging.info("Fetching Other Attachments Data ... ")
    # other_attachments_response, other_attachments_a_doc_status = get_other_attachments(driver)
    data = {
        "finance": {"present": finance_doc_status, "response": finance_response},
        "eform": {"present": eform_doc_status, "response": eform_response},
        # "attachments": {"present": other_attachments_a_doc_status, "response": other_attachments_response},
    }
    if data_push:
        save_to_api(cin, data)


def set_logger():
    log_file_path = os.path.normpath(os.getcwd() + os.sep + os.pardir) + "/logs/" + time.strftime(
        "%Y-%m-%d_%H:%M:%S") + ".log"
    logging.basicConfig(filename=log_file_path,
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)


def remove_error_cin(cin_list_all, cin_list_old):
    cin_list = cin_list_old
    for cin in cin_list_all:
        if cin not in cin_list:
            cin_list.append(cin)
    return cin_list


def start():
    error_cins = []
    cin_list_all = get_all_cin()
    lower_limit = 0
    upper_limit = 250
    cin_list_old = ['U74140HR2015FTC055568', 'U63090GJ2012PTC107088', 'U80903KA2011PTC061427', 'U52390KA2014PTC074986',
                    'U72900KA2008PTC046374', 'U72400KA2014PTC078018', 'U63040MH2005PTC153232', 'U74900KA2015PTC080316',
                    'U72300KA2007PTC041799', 'U74120MH2013FTC247008', 'U72900DL2012PLC241148', 'U72200KA2010PTC054615',
                    'U74999HR2014PTC053030', 'U15209KA2014PTC075887', 'U74140HR2014FTC052854', 'U74999HR2013PTC048853',
                    'U71210KA2012PTC063617', 'U72300HR2006PTC071540', 'U67190MH2014PTC258836', 'U72200KA2007PTC042493',
                    'U80302RJ2015PTC047265', 'U72900KA2016PTC093868', 'U74900KA2011PTC061609', 'U72900DL2017PLC323936',
                    'U74999DL2017PLC321165', 'U74900KA2012PTC062020', 'U63030DL2013PTC256239', 'U93000HR2013PTC051132',
                    'U72200KA2012PTC063551', 'U72300MH2000PLC125441', 'U92413MH2009PTC197424', 'U72900MH2015PTC265614',
                    'U92100MH1995PTC095508', 'U74999DL2018PTC328616', 'U80904MH2015PTC270564', 'U92490MH2019PTC320701',
                    'U74999HR2017PTC070052', 'U74900MH2011PTC220359', 'U72900HR2018FTC077357', 'U72900KA2018PTC112875',
                    'U74140MH2015PTC268131', 'U52100DL2012PTC237371', 'U65100KA2016PTC092879', 'U74999DL2016PTC300195',
                    'U72900MH2015PTC262707', 'U74120MH2015PTC269294', 'U74130KA2010PTC052192', 'U74120MH2015PTC264476',
                    'U74999KA2018PTC117196', 'U74999HR2015FTC056386', 'U74999DL2019PTC345876', 'U72900TG2010FTC068332',
                    'U74999KA2018PTC116465', 'U74999HR2017PTC069568', 'U72900HR2016PTC064845', 'U72900KA2016PTC098673',
                    'U52100MH2011PTC225162', 'U72900KA2016PTC094542', 'U72200KA2015PTC079186', 'U74999HR2018PTC074297',
                    'U72900MH2007PTC171875', 'U74999HR2019PTC077781', 'U72900KA2018PTC110746', 'U74999KA2016PTC127259',
                    'U72200KA2015PTC079230', 'U93030MH2015PTC270628', 'U72200MH2010PTC210076', 'U72200KA2019PTC122146',
                    'U65999KA2018PTC114468', 'U67100KA2015FTC082538', 'U72200KA2013PTC097389', 'U65993KA1993PTC074590',
                    'U74999MH2016PTC287205', 'U74999MH2019PTC320220', 'U24230BR2014PTC023149', 'U74999HR2018PTC077086',
                    'U74999DL2018PTC341083', 'U67190DL2015PTC282441', 'U74999KA2017PTC099619', 'U72900DL2011PTC220728',
                    'U74999KA2017PTC105368', 'U65990JH1995PTC006350', 'U72300DL2015FTC279856', 'U72900MH2015PTC261095',
                    'U72900KA2015PTC084475', 'U74999KA2018PTC109165', 'U72200KA2012PTC086479', 'U72900KA2019PTC126244',
                    'U74999KA2017PTC103903', 'U93000HR2011PTC079866', 'U74900MH2013PTC245166', 'U74999HR2016PTC064093',
                    'U92140MH2013PTC250918', 'U52100MH2012PTC236314', 'U72900KA2011PTC060958', 'U74999KA2018PTC119202',
                    'U74999DL2018PTC337335', 'U74999RJ2019PTC063665', 'U74140DL2015PTC284428', 'U74999DL2017PTC325912',
                    'U74999HR2013PTC051059', 'U74140DL2014PTC273439', 'U74300DL2007PTC158884', 'U72900TN2013PTC090995',
                    'U40300HR2016PTC064528', 'U74120UP2014PTC065536', 'U01403DL2009PTC187455', 'U52399TN2015PTC101215',
                    'U72200KA2010PTC054971', 'U01111DL2016PTC299782', 'U65922HR2016PTC057984', 'U74999KA2018PTC112837',
                    'U74999TG2016PTC110849', 'U72200KA2018PTC113013', 'U74999KA2016PTC096021', 'U50400KA2018PTC109394',
                    'U31401TN2015PTC099911', 'U74140MH2019PTC328769', 'U74999MH2019PTC322765', 'U67200MH2019PTC334521',
                    'U45309DL2017PTC313505', 'U74120UP2013PTC055302', 'U74900KA2016PTC086573', 'U72900DL2018PTC340246',
                    'U74999DL2017PTC310312', 'U72900DL2014PTC267776', 'U80900DL2018PTC334559', 'U72400KA2011PTC057952',
                    'U72200KA2012PTC066894', 'U29299KA2016PTC097757', 'U52600MH2012PTC230136', 'U74999DL2016PTC306016',
                    'U64203KA2011PTC059891', 'U72300TN2013PTC092385', 'U72200DL2015PTC281740', 'U72200PN2015PTC155276',
                    'U74900TN2015PTC101916', 'U52209HR2015PTC054223', 'U74999PN2016PTC164780', 'U33111TG2015PTC097596',
                    'U85195MH1982PTC028194', 'U33125GA2000PTC002909', 'U45100KA2014PTC076441', 'U74999KA2018PTC118469',
                    'U65990HR2018PTC074364', 'U67100DL2020PTC361184', 'U72900KA2018PTC112685', 'U74999KA2020PTC134455',
                    'U51101MH2011PTC224903', 'U52100HR2016PTC058127', 'U67190HR2018PTC073294', 'U72900KA2015PTC080871',
                    'U74900KA2016PTC086953', 'U51900PN2008PTC157070', 'U80900KA2019PTC124204', 'U74999MH2011PTC220994',
                    'U74999DL2014PTC270032', 'U74999GJ2016PTC091839', 'U80903DL2012PTC236595', 'U74999DL2020PTC361607',
                    'U74999KA2017PTC138565', 'U72200KA2016PTC085486', 'U01100HR2019PTC079611', 'U72900KA2018PTC109219',
                    'U72900MH2018PTC312068', 'U74999KA2014PTC074222', 'U92490TG2020PTC140739', 'U74999TG2016PTC110304',
                    'U72900KA2017PTC107963', 'U74999KA2019PTC130599', 'U74140KA2014PTC076210', 'U74999KA2018PTC116260',
                    'U72900KA2019PTC126530', 'U74999MH2017PTC289239', 'U15400RJ2017PTC059188', 'U72900DL2017FTC312487',
                    'U15490MH2019PTC325879', 'U74999KA2016PTC098506', 'U74120UP2015PTC069963', 'U80903DL2010PTC204068',
                    'U74999KA2011PTC058374', 'U85110KA2005PTC037953', 'U15494HR2011PTC043755', 'U85190DL2012PTC268087',
                    'U74999MH2016PTC287898', 'U72200KA2015FTC080705', 'U80211DL1997PLC090156', 'U74999MH2019PTC320625',
                    'U15499DL2002PTC114101', 'U72502KA2017PTC099586', 'U74140DL2012PTC237075', 'U72900DL2013PTC260439',
                    'U67190MH2003PTC139208', 'U63090KA2017PTC099338', 'U85110RJ2003PTC018339', 'U85110KL2009PTC024400',
                    'U72200KA2014FTC077020', 'U52609MH2019PTC328779', 'U72300MH2011PTC215103', 'U15400MH2019PTC322351',
                    'U74140HR2015PTC056764', 'U74900CH2013PTC034657', 'U72900DL2018FTC338921', 'U63040KA2005PLC037834',
                    'U72200MH2013PTC241118', 'U52202TG2020PTC139550', 'U34200TN2015PTC101106', 'U65910DL1996PLC083130',
                    'U72900HR2019PTC083892', 'U72100KA2019PTC120216', 'U80904DL2015PTC287552', 'U74900KA2015PTC084275',
                    'U80903KA2015PTC081485', 'U74999KA2016PTC096884', 'U50400MH2018PTC307759', 'U72200KA2015PTC083534',
                    'U72200KA2016PTC085219', 'U74999DL2015PTC288909', 'U74999KA2012PTC064449', 'U74900KA2015PTC080305',
                    'U74900KA2014PTC077817', 'U74900KA2014PTC074406', 'U72900KA2017PTC102890', 'U72200KA2012PTC065294',
                    'U72200KA2015PTC080781', 'U74999DL2018FTC342198', 'U85100KA2017PTC100587', 'U74999KA2019PTC123901',
                    'U72900DL2010PLC206414', 'U74900TN2015PTC102252', 'U85110RJ2007PTC025459', 'U55101DL2004PTC131219',
                    'U67190TN2008PTC066350', 'U72900KA2019PTC124669', 'U80902TG2020PTC141486', 'U72900MH2019PTC326468',
                    'U72200KA2014PTC073582', 'U51909KA2020PTC134621', 'U40300MH2013PTC248981', 'U74999DL2018PTC331205',
                    'U72900MH2015PTC268297', 'U01400DL2015PTC278774', 'U52100TZ2016PTC022371', 'U74999KL2017PTC050363',
                    'U74140DL2015PTC277272', 'U74999HR2019PTC082217', 'U74999MH2017PTC294895', 'U74120MH2013PTC248969',
                    'U24232TG2011PTC075351', 'U74999KA2019PTC122740', 'U74999MH2019PTC325170', 'U52300MH2013PTC249758',
                    'U72200KA2015FTC082998', 'U72200BR2006PTC011902', 'U72500TG2018PTC128802', 'U72900DL2017PTC311010',
                    'U29220UR2013PTC000567', 'U74999MH2015PTC268665', 'U67120MH1995PTC084946', 'U72100MP2015PTC033773',
                    'U74999KA2017PTC107391', 'U72200KA2014PTC076858', 'U74999KA2019PTC120411', 'U67110KA2015PTC084272',
                    'U72900KA2015PTC080890', 'U65990MH2007PTC171702', 'U74999TG2018PTC123520', 'U74140HR2015PTC054287',
                    'U74999HR2015PTC054222', 'U66010PN2016PLC167410', 'U72300DL2015PTC280282', 'U74900KA2009PTC051174',
                    'U74110GJ2011PTC065512', 'U72400MH2006PTC293037', 'U74999KA2017PTC128777', 'U74900KA2015PTC080321',
                    'U52203DL2015PTC280514', 'U72100KA2015PTC081797', 'U67190TN2020PTC135200', 'U70200MH2019PTC328211',
                    'U72900KA2019PTC128078', 'U74999KA2018PTC133447', 'U72900KA2019PTC124451', 'U74120MH2015FTC265217',
                    'U74999TN2017PTC119779', 'U74200TG2015PTC098960', 'U72900KA2018PTC115685', 'U74999TN2019PTC128346',
                    'U72900UR2015PTC001740', 'U72900MH2016PTC273768', 'U74999MH2016PTC285045', 'U74900KA2012PTC098522',
                    'U74999UP2019PTC116353', 'U74999DL2017PTC310614', 'U72900MP2016PTC040639', 'U74900KA2012PTC063357',
                    'U01122BR2012PTC018117', 'U55204KA2012PTC087024', 'U72200DL2009PTC329543', 'U72900GJ2019FTC108940',
                    'U74120TN2014PTC097963', 'U72900GJ2015PTC085058', 'U93090KA2017PTC101406', 'U74999KA2018PTC112502',
                    'U74140DL2015PTC285635', 'U72900PN2019PTC187678', 'U74999DL2016PTC300035', 'U74999MH2017PTC299322',
                    'U15400KA2018PTC110532', 'U72900KA2017PTC107067', 'U72900DL2012PTC242048', 'U72900DL2011PTC225614',
                    'U74220KA2016PTC093871', 'U24304TZ2019PTC032309', 'U72900GJ2014PTC081539', 'U93090PN2018PTC177783',
                    'U74910DL2019PTC359372', 'U74999BR2017PTC036409', 'U74999HR2015PTC055197', 'U22219KA2007PTC127705',
                    'U15549DL2017PTC315709', 'U72900DL2017PTC318226', 'U09211KA2004PTC034212', 'U72900TG2016PTC111723',
                    'U36100RJ2015PTC047992', 'U72900MH2016PTC272326', 'U63000HR2018PTC077241', 'U74999HR2018PTC076655',
                    'U15202OR2009PTC027213', 'U15100MP2020PTC051347', 'U51397MH2013PTC245092', 'U01409PN2017PTC172439',
                    'U65921DL1993PTC283660', 'U74140DL2012PTC239420', 'U80302DL2018PTC343554', 'U72501KA2016PTC093975',
                    'U74900TN2013PTC092696', 'U74999GJ2018PTC104895', 'U74120TG2016PTC103015', 'U15549HR2009PTC039586',
                    'U51909MH2016PTC281532', 'U74999KA2020PTC133961', 'U74900KA2015PTC080643', 'U65990HR2018PTC075713',
                    'U55209TN2019PTC131757', 'U74999UP2018PTC102725', 'U74140RJ2011PTC054922', 'U74999TN2011PTC080030',
                    'U74140KA2019PTC129875', 'U72900MH2016PTC274099', 'U72200KA2015PTC084422', 'U40100KA2013PTC093769',
                    'U72900KA2020PTC132767', 'U74900DL2015PTC287688', 'U51909DL2007PTC167121', 'U72900HR2018PTC072447',
                    'U74999WB2018PTC228032', 'U65999MH2016PTC285244', 'U74900KA2015PTC082769', 'U74900KA2015PTC080961',
                    'U80902MH2012PTC258559', 'U74999MH2012PTC237035', 'U63090TN2006PTC060723', 'U65999MH2017PTC293038',
                    'U72900DL2017PTC321668', 'U74140KA2015PTC081589', 'U37100UP2017PTC095219', 'U74140DL2015PTC283220',
                    'U74999TG2018PTC127608', 'U74999HR2018PTC073929', 'U93090DL2016PTC307296', 'U72200KA2016PTC085707',
                    'U63000MH2018PTC311923', 'U74120MH2013PTC243214', 'U34102KA2015PTC084804', 'U72900DL2017PTC314668',
                    'U80904HR2017PTC068972', 'U72900KA2019PTC130658', 'U74999KA2018PTC117198', 'U80904MH2018PTC307914',
                    'U72300TG2012PTC083225', 'U17309KA2018PTC110987', 'U74999MH2016PTC286405', 'U74140DL2007PTC157638',
                    'U31900MH2016PTC281796', 'U72300MH1998PTC200508', 'U80100KA2018PTC115606', 'U72900MH2020FTC342404',
                    'U74999GJ2019PTC109847', 'U74999MH2014PTC255614', 'U52609DL2016PTC305606', 'U33111WB2015PTC206772',
                    'U72900HR2015PTC057210', 'U74140MP2011PTC026764', 'U73100DL2015OPC283020', 'U74999DL2017PTC323389',
                    'U52609KA2018PTC116844', 'U01100KL2016PTC045752', 'U93000MH2014PTC259930', 'U80301KA2018PTC111135',
                    'U72200DL2015PTC286534', 'U72200KA2010PTC055487', 'U74999DL2018PTC339087', 'U74999HR2017PTC068437',
                    'U52201WB2016PTC217176', 'U51909MH2016PTC283578', 'U72900DL2019PTC349178', 'U74999KA2018PTC119590',
                    'U72900DL2020PTC360550', 'U74999RJ2016PTC055981', 'U01100TG2018PTC124451', 'U74900MH2013PTC240427',
                    'U80300MH2019PTC325376', 'U85300DL2020PTC364444', 'U80902TG2008PTC062284', 'U72900PB2016PTC045727',
                    'U15122WB2015PTC205829', 'U15100DL2010PTC197532', 'U72300TN1996PTC036958', 'U28931UR2008PTC032573',
                    'U72900DL2012PTC234341', 'U74999TN2014PTC097247', 'U72100HR2013FTC054702', 'U74140RJ2010PTC033722',
                    'L65990MH1994PLC080451', 'U72900DL2020PTC369181', 'U74999OR2018PTC028315', 'U24100DL2014PTC266653',
                    'U72300WB2015PTC207578', 'U72900DL2020PTC366235', 'U72200MH2016PTC282164', 'U29253WB2015PTC207178',
                    'U00000DL2000PLC104823', 'U74900DL2015PTC277145', 'U72200KA2015PTC082063', 'L74140MH1993PLC150054',
                    'U74900KA2011PTC072315', 'U72200DL2015PTC367471', 'U93000KA2015FTC080212', 'U74900DL2009PTC189166',
                    'U72200TG2010PTC070287', 'U72200DL2010PTC211814', 'U72200KA2015PTC081330', 'U72400KA2013PTC072054',
                    'U72200KA2014PTC075775', 'U72200KA2008PTC046105', 'U55204DL2012PTC304447', 'U74900MH2000PTC126237',
                    'U72200TG2007PTC054122', 'U72900PN2009PTC134043', 'U72100MH2005PTC153862', 'U33100DL2008PTC178355',
                    'L74899DL1999PLC101534', 'U74900DL2012PTC230723', 'U72300DL2014PTC271386', 'U72900MH2006PLC162656',
                    'U72200TN2007PTC065476', 'U72900KA2009PTC095554', 'U74999KA2012PTC121445', 'U22190TN2016PTC109929',
                    'U72300KA2013PTC087276', 'U34100KA2016PTC095926', 'U34104PN2010PTC135855', 'U34200MH2015PTC269308',
                    'U34300GJ2017PTC097818', 'U34300KA2017PTC107271', 'U51900TZ2008PTC017628', 'U34201KA2015PTC082126',
                    'U31909KA2016PTC096370', 'U31101PN2011PLC139837', 'U34100TN2015PTC100789', 'U74999MH2011PTC221931',
                    'U72200TN2008PTC068575', 'U72900KA2019PTC125454', 'U72900DL2012PTC235129', 'U67100DL1998PTC093878',
                    'U72900RJ2020PTC069713', 'U72900MH2010PLC203640', 'U72900KA2019PTC127225', 'U72200KA2012PTC064709',
                    'U72100TN2005PTC057463', 'U55101TN2015PTC099325', 'U72200HR2019PTC080437', 'U74200MH2005PTC192623',
                    'U72200KL2014PTC037700', 'U72200GJ2001PTC100083', 'U74900MH2016PTC272534', 'U72300WB2015PTC208356',
                    'U72100MH2004PTC148510', 'U72300MH2011PTC222535', 'U65190MH2015PTC270609', 'U74900WB2014PTC203082',
                    'U74999MH2006PTC160835', 'U74110HR2014PTC072465', 'U74120TG2012PTC084551', 'U74999MH2014PTC260247',
                    'U74999MH2015PTC261546', 'U72900GJ2007PLC109642', 'U72300KA2000PTC027842', 'U72300GA2009PTC007713',
                    'U72200HR2015PTC057197', 'U72200KA2000PTC028279', 'U51909DL2011PTC218346', 'U72900HR2019PTC083892',
                    'U74140DL2015PTC285986', 'U65929KA2018PLC116815', 'U63090KA2012FTC065834', 'U24297HR2013PTC048437',
                    'U63000KA2016PTC094011', 'U51100PN2010PTC136340', 'U74120HR2012PTC092506', 'U74999MH2020PTC346361',
                    'U31904DL2019PTC357706', 'U67190DL2016PLC300962', 'U74999KA2016PTC093524', 'U74999HR2018PTC076100',
                    'U72900MH2021PTC52885', 'U72900HR2019PTC078467', 'U72900DL2020PTC359786', 'U74999KA2019PTC130740',
                    'U74994KA2020PTC136573', 'U85100KA2014PTC076229', 'U74999MH2014PTC259739', 'U80902KA2019PTC125954']

    #cin_list = ['U93030DL2010PTC198141']
    #cin_list = cin_list_all
    #cin_list_old = ['U74999MH2014PTC259739', 'U85100KA2014PTC076229', 'U72900MH2021PTC52885', 'U24297HR2013PTC048437', 'U74900WB2014PTC203082', 'U65190MH2015PTC270609', 'U74900MH2016PTC272534', 'U72200GJ2001PTC100083', 'U72200KL2014PTC037700', 'U74200MH2005PTC192623', 'U72200HR2019PTC080437', 'U72100TN2005PTC057463', 'U72900KA2019PTC127225', 'U72900MH2010PLC203640', 'U72900RJ2020PTC069713', 'U67100DL1998PTC093878', 'U72900DL2012PTC235129', 'U74999MH2011PTC221931', 'U34300KA2017PTC107271', 'U34200MH2015PTC269308', 'U34104PN2010PTC135855', 'U72300KA2013PTC087276', 'U72900KA2009PTC095554', 'U72900MH2006PLC162656', 'U72300DL2014PTC271386', 'L74899DL1999PLC101534', 'U33100DL2008PTC178355', 'U72900PN2009PTC134043', 'U72200TG2007PTC054122', 'U72200KA2008PTC046105', 'U72200KA2014PTC075775', 'U72400KA2013PTC072054', 'U72200KA2015PTC081330', 'U72200DL2010PTC211814', 'U93000KA2015FTC080212', 'U00000DL2000PLC104823', 'U72200MH2016PTC282164', 'U72900DL2020PTC366235', 'U24100DL2014PTC266653', 'L65990MH1994PLC080451', 'U72300TN1996PTC036958', 'U15100DL2010PTC197532', 'U15122WB2015PTC205829', 'U72900PB2016PTC045727', 'U80902TG2008PTC062284', 'U80300MH2019PTC325376', 'U72900DL2019PTC349178', 'U52201WB2016PTC217176', 'U74999HR2017PTC068437', 'U72200KA2010PTC055487', 'U72200DL2015PTC286534', 'U80301KA2018PTC111135', 'U93000MH2014PTC259930', 'U01100KL2016PTC045752', 'U52609KA2018PTC116844', 'U73100DL2015OPC283020', 'U33111WB2015PTC206772', 'U52609DL2016PTC305606', 'U74999MH2014PTC255614', 'U74999GJ2019PTC109847', 'U31900MH2016PTC281796', 'U74140DL2007PTC157638', 'U74999MH2016PTC286405', 'U72300TG2012PTC083225', 'U80904MH2018PTC307914', 'U72900DL2017PTC314668', 'U34102KA2015PTC084804', 'U74140DL2015PTC283220', 'U37100UP2017PTC095219', 'U74900DL2015PTC287688', 'U72900MH2016PTC274099', 'U74140KA2019PTC129875', 'U55209TN2019PTC131757', 'U74999KA2020PTC133961', 'U74900TN2013PTC092696', 'U72501KA2016PTC093975', 'U80302DL2018PTC343554', 'U01409PN2017PTC172439', 'U15100MP2020PTC051347', 'U72900TG2016PTC111723', 'U09211KA2004PTC034212', 'U15549DL2017PTC315709', 'U22219KA2007PTC127705', 'U74220KA2016PTC093871', 'U72900DL2012PTC242048', 'U74140DL2015PTC285635', 'U93090KA2017PTC101406', 'U72900GJ2015PTC085058', 'U74120TN2014PTC097963', 'U01122BR2012PTC018117', 'U74999UP2019PTC116353', 'U74120MH2015FTC265217', 'U72900KA2019PTC124451', 'U72900KA2019PTC128078', 'U74999KA2017PTC128777', 'U74999KA2019PTC120411', 'U72200KA2014PTC076858', 'U29220UR2013PTC000567', 'U72900DL2017PTC311010', 'U72500TG2018PTC128802', 'U72200BR2006PTC011902', 'U72200KA2015FTC082998', 'U74120MH2013PTC248969', 'U74999HR2019PTC082217', 'U72900MH2015PTC268297', 'U74999DL2018PTC331205', 'U51909KA2020PTC134621', 'U80902TG2020PTC141486', 'U72900KA2019PTC124669', 'U55101DL2004PTC131219', 'U74999KA2019PTC123901', 'U72200KA2012PTC065294', 'U74900KA2014PTC077817', 'U74900KA2015PTC080305', 'U72200KA2016PTC085219', 'U74999KA2016PTC096884', 'U74900KA2015PTC084275', 'U65910DL1996PLC083130', 'U63040KA2005PLC037834', 'U72900DL2018FTC338921', 'U67190MH2003PTC139208', 'U85190DL2012PTC268087', 'U74120UP2015PTC069963', 'U74999KA2016PTC098506', 'U15490MH2019PTC325879', 'U74140KA2014PTC076210', 'U74999TG2016PTC110304', 'U74999DL2014PTC270032', 'U45100KA2014PTC076441', 'U33125GA2000PTC002909', 'U85195MH1982PTC028194', 'U74999PN2016PTC164780', 'U72200PN2015PTC155276', 'U29299KA2016PTC097757', 'U72900DL2014PTC267776', 'U74999KA2016PTC096021', 'U74999TG2016PTC110849', 'U40300HR2016PTC064528', 'U74300DL2007PTC158884', 'U74140DL2014PTC273439', 'U74999HR2013PTC051059', 'U74999RJ2019PTC063665', 'U74999DL2018PTC337335', 'U72900KA2011PTC060958', 'U72900KA2019PTC126244', 'U72200KA2012PTC086479', 'U72900KA2015PTC084475', 'U72300DL2015FTC279856', 'U67190DL2015PTC282441', 'U74999DL2018PTC341083', 'U65999KA2018PTC114468', 'U72200KA2019PTC122146', 'U72200KA2015PTC079230', 'U74999KA2016PTC127259', 'U72900MH2007PTC171875', 'U74120MH2015PTC264476', 'U74999DL2016PTC300195', 'U65100KA2016PTC092879', 'U74140MH2015PTC268131', 'U72900KA2018PTC112875', 'U72900HR2018FTC077357', 'U74999DL2018PTC328616', 'U72900MH2015PTC265614', 'U92413MH2009PTC197424', 'U72300MH2000PLC125441', 'U93000HR2013PTC051132', 'U63030DL2013PTC256239', 'U72200TG2012PTC080822', 'U72300DL2014PTC270509', 'U93000UP2014PTC064870', 'U72300DL2015PTC279342', 'U67200DL2018PLC329710', 'U65999DL2016PLC304713', 'U51909DL2018PTC339012', 'U74900KA2011PTC061609', 'U72200KA2008PTC048012', 'U74999MH2015PTC268012', 'U93090MH2018PTC308253', 'U72200KA2007PTC042493', 'U72300HR2006PTC071540', 'U85100PN2013PTC178255', 'U74999HR2013PTC048853', 'U72200KA2010PTC054615', 'U67190MH2012PTC337657', 'U74140DL2015PTC281694', 'U63040MH2005PTC153232', 'U74900KA2014PTC077652', 'U74140DL2014PTC274413', 'U52390KA2014PTC074986', 'U74999KA2012PTC062610', 'U74990MH2011PTC220126', 'U74140DL2011FTC226246', 'U74130KA2005PTC087280', 'U93030DL2010PTC198141']
    #cin_list = remove_error_cin(cin_list_all, cin_list_old)
    #cin_list.reverse()
    import json
    cin_list_old = []
    with open('/home/ubuntu/code/entracker-crawler/error/last_error_file.json','r') as f:
       error_data = json.load(f)
    for data in error_data:
       cin_list_old.append(data.get('cin'))
    #cin_list = cin_list_all
    cin_list = remove_error_cin(cin_list_all, cin_list_old)
    print("TOTAL :", len(cin_list))
    cin_list = cin_list[lower_limit:]
    for cin in cin_list:
        driver = start_driver()
        cin = cin.strip()
        try:
            searching_cin(lower_limit, driver, cin, data_push=True)
        except Exception as e:
            error_cins.append({"cin": cin, "error": str(e)})
        driver.quit()
        if lower_limit % 2 == 0 and lower_limit != 50 and lower_limit != 100:
            logging.info("waiting After 2 consequtive requests  ")
            time.sleep(15)
        if lower_limit % 50 == 0 and lower_limit != 100:
            logging.info("waiting After 50 consequtive requests  ")
            time.sleep(40)
        if lower_limit % 100 == 0:
            logging.info("waiting After 100 consequtive requests  ")
            time.sleep(50)
        time.sleep(random.randint(5, 10))
        lower_limit = lower_limit + 1
    error_file_path = os.path.normpath(os.getcwd() + os.sep + os.pardir) + "/error/" + time.strftime(
        "%Y-%m-%d_%H:%M:%S") + ".json"
    with open(error_file_path, "w") as f:
        f.write(json.dumps(error_cins, indent=4))
    logging.info(" No of CIN errors found : " + str(len(error_cins)))
    print(json.dumps(error_cins))


if __name__ == '__main__':
    # driver = start_driver()
    # print("Start driver ...")
    # driver.quit()
    set_logger()
    start()
