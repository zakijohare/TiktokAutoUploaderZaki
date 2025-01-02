from .cookies import load_cookies_from_file, save_cookies_to_file
from fake_useragent import UserAgent, FakeUserAgentError
import undetected_chromedriver as uc
import threading, os


WITH_PROXIES = False

class Browser:
    __instance = None

    @staticmethod
    def get():
        if Browser.__instance is None:
            with threading.Lock():
                if Browser.__instance is None:
                    Browser.__instance = Browser()
        return Browser.__instance

    def __init__(self):
        if Browser.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Browser.__instance = self
        self.user_agent = ""
        self.proxy = None
        self._driver = None
        self._init_driver()
        
    def _init_driver(self):
        """Initialize the Chrome driver with current options"""
        options = uc.ChromeOptions()
        if self.proxy:
            # Format proxy for Chrome
            proxy_str = self.proxy
            if '@' in self.proxy:
                # Handle authenticated proxy
                auth, proxy = self.proxy.split('@')
                protocol = proxy_str.split('://')[0]
                options.add_argument(f'--proxy-server={protocol}://{proxy}')
                # Add proxy auth extension
                auth = auth.split('://')[1]
                username, password = auth.split(':')
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
                """ % (proxy.split(':')[0], proxy.split(':')[1], username, password)
                
                import tempfile
                import zipfile
                
                pluginfile = 'proxy_auth_plugin.zip'
                with zipfile.ZipFile(pluginfile, 'w') as zp:
                    zp.writestr("manifest.json", manifest_json)
                    zp.writestr("background.js", background_js)
                options.add_extension(pluginfile)
            else:
                # Simple proxy without auth
                options.add_argument(f'--proxy-server={proxy_str}')
                
        self._driver = uc.Chrome(options=options)
        self.with_random_user_agent()
        
    def set_proxy(self, proxy):
        """Set proxy for the browser"""
        if not proxy.startswith(('http://', 'https://')):
            proxy = 'http://' + proxy
            
        self.proxy = proxy
        
        # Reinitialize driver with new proxy settings
        if self._driver:
            self._driver.quit()
        self._init_driver()

    def with_random_user_agent(self, fallback=None):
        """Set random user agent.
        NOTE: This could fail with `FakeUserAgentError`.
        Provide `fallback` str to set the user agent to the provided string, in case it fails. 
        If fallback is not provided the exception is re-raised"""

        try:
            self.user_agent = UserAgent().random
        except FakeUserAgentError as e:
            if fallback:
                self.user_agent = fallback
            else:
                raise e

    @property
    def driver(self):
        return self._driver

    def load_cookies_from_file(self, filename):
        cookies = load_cookies_from_file(filename)
        for cookie in cookies:
            self._driver.add_cookie(cookie)
        self._driver.refresh()

    def save_cookies(self, filename: str, cookies:list=None):
        save_cookies_to_file(cookies, filename)


if __name__ == "__main__":
    import os
    # get current relative path of this file.
    print(os.path.dirname(os.path.abspath(__file__)))
