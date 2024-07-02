import re
import time
import os
import datetime
import zipfile
from datetime import timedelta
from email.message import EmailMessage
import smtplib
from fake_useragent import UserAgent
from configparser import ConfigParser
from dateutil import parser
import csv
import glob
from selenium import webdriver
from io import StringIO
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from mysql.connector import MySQLConnection
from CustomLogGenerator import CustomLogGenerator
import chromedriver_autoinstaller
import requests
import pandas as pd
from bs4 import BeautifulSoup

config = ConfigParser()
_dir_name = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(_dir_name,'config.ini')
config.read(config_file)
chromedriver_autoinstaller.install()

to_email: str = config['mail_sender']['to_email']
from_email: str = config['mail_sender']['from_email']
dwnpath: str = config['path']['download_path']
log_path: str = config['path']['log_path']
log_filename: str = config['path']['log_filename']
referrer: str = config['headers']['referrer']
accept: str = config['headers']['accept']
content: str = config['headers']['content-type']
# CustomLogGenerator class instance defined in another file
filename = CustomLogGenerator(log_path, log_filename)
au = UserAgent()


class Information:
    download_count = 0
    downloaded_files = []

    @staticmethod
    def get_time(formatdate: str, post_date: int = None):
        #  get the current time from instance
        xtime = datetime.datetime.now()
        get_time: str = time.strftime(formatdate)

        # if the post-date parameter passed then return the desire date
        if post_date:
            post_date_back = xtime - datetime.timedelta(post_date)
            get_time = post_date_back.strftime(formatdate)
            return get_time

        return get_time

    @staticmethod
    def convert_datetime_format(datetime_string: str, date_format: str):
        # Check if the datetime string is in the "X hours ago" or "X minutes ago" format
        if datetime_string.endswith(" ago"):
            parts = datetime_string.split()
            if len(parts) == 3:
                duration = int(parts[0])
                unit = parts[1]

                now = datetime.datetime.now()
                if unit.startswith("hour"):
                    delta = timedelta(hours=duration)
                elif unit.startswith("minute"):
                    delta = timedelta(minutes=duration)
                elif unit.startswith("second"):
                    delta = timedelta(seconds=duration)
                else:
                    return None

                converted_datetime = now - delta
                return converted_datetime.strftime(date_format)

        try:
            # Parse the datetime string to a datetime object
            dt = parser.parse(datetime_string)

            # Format the datetime object to the desired format
            formatted_datetime = dt.strftime(date_format)

            return formatted_datetime

        except parser.ParserError:
            return None

    @staticmethod
    def db_connection(host, port, username, password, database):
        try:
            mydb = MySQLConnection(
                port=port,
                host=host,
                user=username,
                password=password,
                database=database
            )
            print("Database connection established.")
            return mydb
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

    @staticmethod
    def make_csv_file(data_list: list, filename: str, col_header: list = None):

        try:
            if col_header is None:
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = data_list[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in data_list:
                        writer.writerow(row)
                return filename

            else:
                if not filename.endswith('.csv'):
                    filename += '.csv'

                with open(filename, 'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    if col_header:
                        writer.writerow(col_header)
                    writer.writerows(data_list)

            return f"{filename}"
        except Exception as e:
            print(f"make_csv_file {e}")

    @staticmethod
    def extract_zip(zip_path, extract_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

    @staticmethod
    def change_filename(name: str, download_path: str):

        current_time = Information.get_time("%d_%m_%Y")
        filename = f'{name}_{current_time}'

        home = os.path.expanduser('~')
        path = os.path.join(home, download_path)
        path_a = path + "/*"
        list_of_files = glob.glob(path_a)
        latest_file = max(list_of_files, key=os.path.getctime)
        _, original_extension = os.path.splitext(latest_file)
        new_file = os.path.join(path, filename + original_extension)
        os.rename(latest_file, new_file)
        details = f"file created : {new_file}"

        return details

    @staticmethod
    def log(msg):
        return filename.generate_log(msg)

    @staticmethod
    def send_mail(subject, details, logfilename=None):
        msg = EmailMessage()
        log_message = "Automated log message: Crawler Log"
        disclaimer_message = "Disclaimer: Please do not reply to this email. This email was automatically generated."

        msg['From'] = from_email
        msg['To'] = ', '.join(config.get('Recipients', r) for r in config.options('Recipients'))
        msg["subject"] = f'{subject}'

        # msg_body = f"{details}\n\n{log_message}\n\n{disclaimer_message}"
        # msg.set_content(msg_body)
        html_content = f"<p style='color: black;'>{details}</p>\n\n" \
                       f"<p style='color: blue;'>{log_message}</p>\n\n" \
                       f"<p style='color: blue;'>{disclaimer_message}</p>"

        msg.add_alternative(html_content, subtype='html')
        if logfilename:
            # msg.set_content(f"{log_message}\n\n{disclaimer_message}")
            with open(logfilename, 'r') as f:
                data = f.read()
            msg.add_attachment(data, filename="Details.log")

        try:
            with smtplib.SMTP(config['mail_sender']['host'], int(config['mail_sender']['port'])) as server:
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
            Information.log(f"Failed to send email: {e}")

    @staticmethod
    def get_driver_inst(download_path=None, return_driver=False):

        # set the all cookies and block web notifications
        chrome_option = Options()
        chrome_option.add_argument('--disable-notifications')
        chrome_option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                                   "like Gecko) Chrome/92.0.4515.131 Safari/537.36")

        if return_driver:
            chrome_option.add_argument('--headless')

            chrome_option.add_argument('--disable-features=V9DownloadWithDownloadPreference')

        if download_path:
            prefs = {
                'download.default_directory': download_path,
                'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True
            }
            chrome_option.add_experimental_option("prefs", {
                "profile.managed_default_content_settings.javascript": 2  # Disable JavaScript alerts
            })

            chrome_option.add_experimental_option('prefs', prefs)

            chrome_option.add_argument("--disable-notifications")

            chrome_option.add_argument('--disable-features=V9DownloadWithDownloadPreference')

        driver = webdriver.Chrome(options=chrome_option)
        return driver

    @staticmethod
    def bs4_source(url: str, headers=None):
        if headers is None:
            headers = {}  # Initialize headers as an empty dictionary if not provided

        response = requests.get(url, headers=headers, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')

        return soup

    @staticmethod
    def get_source(url: str):

        with Information.get_driver_inst(return_driver=True) as driver:
            driver.get(url)
            current_window_state = driver.execute_script("return window.innerWidth == screen.width")

            if not current_window_state:
                # Maximize the window if it's not already maximized
                driver.maximize_window()
                time.sleep(5)

            soup = BeautifulSoup(driver.page_source, 'html.parser')

        return soup

    def remove_special_chars(self, text):
        return re.sub(r'[^\w\s]', '', text)

    @staticmethod
    def get_json_response(link, headers=None):

        with requests.session() as session:
            response = session.get(link, headers=headers)

            response.raise_for_status()

            if response.status_code == 200:
                if 'application/json' in response.headers.get('content-type', ''):
                    result_data = response.json()
                else:
                    result_data = pd.read_html(response.text)

                return result_data

    @staticmethod
    def getresponse(link):
        try:
            headers = {
                'User-Agent': au.random,
                'Accept': accept
            }
            with requests.session() as session:
                if 'Referer' in headers:
                    session.get(headers['Referer'], headers=headers)

                response = session.get(link, headers=headers)

                response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx status codes)

                if response.status_code == 200:
                    if 'application/json' in response.headers.get('content-type', ''):
                        result = response.json()
                    else:
                        # result = pd.read_html(response.text)
                        result = pd.read_html(StringIO(response.text))

                        if isinstance(result, list):
                            # Concatenate DataFrames into a single DataFrame
                            result = pd.concat(result[3:], ignore_index=True)

                            # Ensure the DataFrame has shape (1, 27, 17)
                            # Assuming 'data' is a DataFrame, you can directly reshape it
                        result = result.values.reshape((27, 17))

                    return result
        except requests.exceptions.HTTPError as err:
            print(f"Error accessing {link}: {err}")
            return None, None, None

    def download_file(self, file_url, local_file_path, headers=None):

        try:
            session = requests.session()
            if headers is not None:
                response = session.get(file_url, verify=False, headers=headers, timeout=5)
            else:
                response = session.get(file_url, verify=False, timeout=5)

            if response.status_code == 404:
                print(f"[ERROR]-Error downloading {file_url}: 404 Not Found")
                return None, None

            response.raise_for_status()
            _, local_file_extension = os.path.splitext(local_file_path)
            if not local_file_extension:
                _, file_extension = os.path.splitext(file_url)
                local_file_path += file_extension

            if not os.path.exists(local_file_path):
                self.download_count += 1
                with open(local_file_path, 'wb') as file:
                    file.write(response.content)
                self.log(f"[INFO]-Downloading --- {local_file_path}")
                self.downloaded_files.append(local_file_path)

                return str(self.download_count), local_file_path

            else:
                self.log(f"[INFO]-file exist in the directory : {local_file_path}")

                return str(self.download_count), local_file_path

        except (requests.exceptions.RequestException, IOError) as e:
            print(f"[ERROR]-Error downloading {file_url}: {e}")
            return None, None



