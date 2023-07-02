#<!----- Imports ----->
import requests
from requests.adapters import HTTPAdapter, Retry

from bs4 import BeautifulSoup
import random, time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#<!----- Default Declarations ----->
DEFAULT_TIMEOUT_s = 5 #seconds

#<!----- Classes ----->
class TimeoutHTTPAdapter(HTTPAdapter):
    #Courtesy of https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT_s
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)

class req:
    def __init__(self,MIN_TIME_BET_REQ_s:float = 1):
        self.MIN_TIME_BET_REQ_s = MIN_TIME_BET_REQ_s #seconds
        self.DEFAULT_TIMEOUT_s = DEFAULT_TIMEOUT_s  #seconds
        self.last_request = time.time()
        self.headers = self.default_headers(self._get_new_useragent())

    @staticmethod
    def useragent_list()-> list:
        return ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36', 
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36', 
        'Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148', 
        'Mozilla/5.0 (Linux; Android 11; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Mobile Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0'] 

    @staticmethod
    def default_headers(useragent: str) -> dict:
        return {'User-Agent': useragent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-CA,en-US;q=0.7,en;q=0.3',
        'Connection': 'keep-alive',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
        }

    @staticmethod
    def default_referers() -> list:
        return ['','https://www.google.com/']

    def _get_new_useragent(self) -> str:
        if (not hasattr(self, "_list_of_useragent")) or (self._list_of_useragent == []):
            self._list_of_useragent = self.useragent_list()
            random.shuffle(self._list_of_useragent)
        return self._list_of_useragent.pop()

    def _get_new_referer(self) -> str:
        if (not hasattr(self, "_list_of_referer")) or (self._list_of_referer == []):
            self._list_of_referer = self.default_referers()
            random.shuffle(self._list_of_referer)
        return self._list_of_referer.pop()


    def _change_useragent(self) -> None:
        """Change request useragent to random one
        """
        self.headers['User-Agent'] = self._get_new_useragent()

    def _change_referer(self):
        self.headers['Referer'] = self._get_new_referer()
    
    def get_from_list(self, url_list:list[str], randomize_useragent:bool=False, randomize_referer:bool=False, custom_headers:dict =None, allow_redirects: bool=True, verify_ssl:bool = True) -> list[requests.Response]:
        """Complete requests to a list of urls and return the list of responses
        """
        duplicate_list = url_list[:]
        random.shuffle(duplicate_list)

        req = {}
        for url in duplicate_list:
            req[url] = self.get(url, randomize_useragent=randomize_useragent, randomize_referer=randomize_referer, custom_headers=custom_headers, allow_redirects=allow_redirects, verify_ssl=verify_ssl)
        
        return [req[url] for url in url_list]
    
    def get(self, url, randomize_useragent:bool=False, randomize_referer:bool=False, timeout:float =None, retry:int = 5, custom_headers:dict=None, allow_redirects:bool=True, verify_ssl:bool=True, data:dict=None) -> requests.Response:
        """URL request with header randomization, timeout, and retries builtin

        Args:
            url (str): URL to request
            randomize_header (bool, optional): Randomize useragent and referer. Defaults to False.
            timeout (float, optional): request timeout. Defaults to None.
            retry(bool, optional): Number of times to retry on failure, Defaults to 5
            custom_headers(dict, optional): Custom headers, Defaults to None

        Returns:
            request object: request object
        """        
        if randomize_referer:
            self._change_referer()
        if randomize_useragent:
            self._change_useragent()

        if custom_headers:
            headers = custom_headers
        else:
            headers = self.headers
        
        if not timeout:
            timeout = self.DEFAULT_TIMEOUT_s

        time_elapsed = time.time() - self.last_request
        time.sleep(max(0, self.MIN_TIME_BET_REQ_s - time_elapsed))
        for i in range(retry):
            try:
                res = requests.get(
                    url, 
                    headers=headers, 
                    timeout=timeout, 
                    allow_redirects=allow_redirects,
                    verify=verify_ssl)
                res.raise_for_status()
                break
            except Exception as e:
                time.sleep(0.5 * (2 ** (i)))
                res = None
        return res

    def create_session(self, retry:int = 5) -> requests.Session:
        """Generate sessions object with adequate headers and adapters

        Args:
            retry (int, optional): Number of times to retry on failed request. Defaults to 5.

        Returns:
            sessions obj: sessions object
        """
        s = requests.Session()
        s.headers = self.headers
        retries = Retry(total=retry,
                        backoff_factor=0.5,
                        status_forcelist=[429, 500, 502, 503, 504],
                        method_whitelist=["HEAD", "GET", "OPTIONS"]
                        )
        s.mount('http://', TimeoutHTTPAdapter(max_retries=retries))
        s.mount('https://', TimeoutHTTPAdapter(max_retries=retries))
        self.session = s
        return s

    def session_get(self, url: str, custom_headers: dict = None, data:dict = None) -> requests.Response:
        if custom_headers:
            headers = custom_headers
        else:
            headers = self.headers

        return self.session.get(url, data=data, headers=headers)
    
    def session_get_from_list(self, url_list:list[str], data:dict=None, custom_headers:dict=None) -> list[requests.Response]:
        duplicate_list = url_list[:]
        random.shuffle(duplicate_list)

        req = {}
        for url in duplicate_list:
            req[url] = self.session_get(url, custom_headers=custom_headers, data=data)
        
        return [req[url] for url in url_list]

    def __repr__(self) -> str:
        return f"req(MIN_TIME_BET_REQ_s={self.MIN_TIME_BET_REQ_s})"

    def __str__(self) -> str:
        class_def = f"""
        Requests Class
        Min time between requests   : {self.MIN_TIME_BET_REQ_s:.2f}s
        Default Timeout             : {self.DEFAULT_TIMEOUT_s:.2f}s
        Headers:
        """

        header_def = ""
        for key, value in self.headers.items():
            header_def += f"{key}:{value}\n"
        
        return class_def + header_def

class BS:
    def __init__(self) -> BeautifulSoup:
        self.bs = BeautifulSoup
        return self.bs

    def get_soup(self, res:str):
        return self.bs(res.text, "html.parser")
    
    def get_soup_list(self, res_text_list: list[str]) -> list:
        return [self.get_soup(res_text) for res_text in res_text_list]
    
    def __repr__(self) -> str:
        return "BS()"

    def __str__(self) -> str:
        return "Beautifulsoup class with useful function methods"