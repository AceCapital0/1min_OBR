import json
import logging
import pandas as pd
import datetime
import requests
import click
from requests.models import Response
from six.moves.urllib.parse import urljoin
from kiteconnect import KiteConnect
import kiteconnect.exceptions as ex
from bs4 import BeautifulSoup
import pyotp
 
import sys
sys.setrecursionlimit(1500)



log = logging.getLogger(__name__)

base_url = "https://kite.zerodha.com"
login_url = "https://kite.zerodha.com/api/login"
twofa_url = "https://kite.zerodha.com/api/twofa"
instruments_url = "https://api.kite.trade/instruments"

class Zerodha(KiteConnect):
    _default_root_uri = "https://kite.zerodha.com"
    def __init__(self, user_id=None, password=None, twofa=None):
    
        self.user_id = user_id
        self.password = password
        self.twofa = twofa
    
        super().__init__(api_key="")
        self.s = self.reqsession = requests.Session()
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                    }
        self.reqsession.headers.update(headers)
        self.chunkjs = {}
        self.url_patch = '/oms'


    def load_creds(self, user_id,password,twofa,TOTP=False):
        self.user_id = user_id
        self.password = password
        self.twofa = twofa

    def _user_agent(self):
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
    
    def login_step1(self):
        self.r = self.reqsession.get(base_url)
        self.r = self.reqsession.post(login_url, data={"user_id": self.user_id, "password":self.password})
        j = json.loads(self.r.text)
        return j

    def login_step2(self, j):
        authkey = (pyotp.TOTP(self.twofa)).now()
        #print(authkey)
        data = {"user_id": self.user_id, "request_id": j['data']["request_id"], "twofa_value": authkey }
        self.r = self.s.post(twofa_url, data=data)
        j = json.loads(self.r.text)
        return j


    def login(self):
        j = self.login_step1()
        if j['status'] == 'error':
            raise Exception(j['message'])
        
        j = self.login_step2(j)
        print(j)
        if j['status'] == 'error':
            raise Exception(j['message'])
        self.enc_token = self.r.cookies['enctoken']
        self.a = self.instruments('NFO')
        return j

    def custom_headers(self):
        h = {}
        h['authorization'] = "enctoken {}".format(self.enc_token)
        h['referer'] = 'https://kite.zerodha.com/dashboard'
        h['x-kite-version'] = '2.9.2'
        h['sec-fetch-site'] = 'same-origin'
        h['sec-fetch-mode'] = 'cors'
        h['sec-fetch-dest'] = 'empty'
        h['x-kite-userid'] = self.user_id
        return h
    
    def _request(self, route, method, url_args=None, params=None,
                 is_json=False, query_params=None):
        if url_args:
            uri = self._routes[route].format(**url_args)
        else:
            uri = self._routes[route] 

        url = urljoin(self.root, self.url_patch + uri)
        
        # prepare url query params
        if method in ["GET", "DELETE"]:
            query_params = params


        # Custom headers
        headers = self.custom_headers()

        if self.debug:
            log.debug("Request: {method} {url} {params} {headers}".format(method=method, url=url, params=params, headers=headers))

        try:
            r = self.reqsession.request(method,
                                        url,
                                        json=params if (method in ["POST", "PUT"] and is_json) else None,
                                        data=params if (method in ["POST", "PUT"] and not is_json) else None,
                                        params=query_params,
                                        headers=headers,
                                        verify=not self.disable_ssl,
                                        allow_redirects=True,
                                        timeout=self.timeout,
                                        proxies=self.proxies)
            self.r = r
        except Exception as e:
            raise e

        if self.debug:
            log.debug("Response: {code} {content}".format(code=r.status_code, content=r.content))

        # Validate the content type.
        if "json" in r.headers["content-type"]:
            try:
                data = json.loads(r.content.decode("utf8"))
            except ValueError:
                raise ex.DataException("Couldn't parse the JSON response received from the server: {content}".format(
                    content=r.content))

            # api error
            if data.get("status") == "error" or data.get("error_type"):
                # Call session hook if its registered and TokenException is raised
                if self.session_expiry_hook and r.status_code == 403 and data["error_type"] == "TokenException":
                    self.session_expiry_hook()

                # native Kite errors
                exp = getattr(ex, data.get("error_type"), ex.GeneralException)
                raise exp(data["message"], code=r.status_code)

            return data["data"]
        elif "csv" in r.headers["content-type"]:
            return r.content
        else:
            raise ex.DataException("Unknown Content-Type ({content_type}) with response: ({content})".format(
                content_type=r.headers["content-type"],
                content=r.content))
    
    def get_chunk_js(self):
        self.r = self.reqsession.get(urljoin(base_url, '/dashboard'))
        html = self.r.text
        bs = BeautifulSoup(html)
        for tag in bs.find_all("link"):
            src = tag.attrs.get("href", "")
            # print(src)
            if "chunk" in src:
                break
        url = urljoin(base_url, tag.attrs.get("href"))
        self.r = self.reqsession.get(url)
        return self.r.text
    
    def chunk_to_json(self, js):
        start = js.find('{"months"')
        end = js.find("\')}}])")
        jtxt = js[start:end].replace('\\','')
        self.chunkjs = json.loads(jtxt)
        return self.chunkjs
    
 
    def instruments(self, exchange=None):

        for i in range(0,3):
            try:
                if exchange:
                    self.r = self.reqsession.get(instruments_url + "/{}".format(exchange))
                else:
                    self.r = self.reqsession.get(instruments_url)
                return self._parse_instruments(self.r.text)
            except Exception as e:
                if 'Incorrect `api_key` or `access_token`.' in str(e):
                    self.login()
                    continue
                else:
                    raise
 

    #Get Instrument Token
    def get_instrument_token(self, exchange, stock):
        instrument_token = None
        for _a in self.a:
            if _a['tradingsymbol'] == stock and _a['exchange'] == exchange:
                instrument_token = _a['instrument_token']
            else:
                pass

        if instrument_token is None:
            print(stock + " Invalid symbol.")
            return None  # error. wrong symbol
        else:
            return int(instrument_token) # successful

    def fetch_latest_historical_data(self, exchange, stock, interval="5minute"):
        if interval == "minute":
            time_delta = 6
        elif interval == "3minute" or interval == "5minute" or interval == "10minute":
            time_delta = 21
        elif interval == "15minute" or interval == "30minute":
            time_delta = 25
        elif interval == "60minute":
            time_delta = 60
        else:
            time_delta = 29
        instrument_token = self.get_instrument_token(exchange, stock)
        if instrument_token is None:
            return None
        else:
            to_date = datetime.datetime.today()
            from_date = datetime.datetime.today() - datetime.timedelta(time_delta)
            df = None

            for i in range(0, 100):
                try:
                    df = pd.DataFrame(self.historical_data(instrument_token, from_date, to_date, interval))
                    df['dateonly'] = df['date'].dt.strftime('%d-%m-%Y')  # extract date only
                    df['timeonly'] = df['date'].dt.strftime('%H:%M:%S')  # extract time only
                    df = df.loc[:, df.columns != 'date']
                    break
                except Exception as e:
                    raise
                    time_delta -= 1
                    from_date = datetime.datetime.today() - datetime.timedelta(time_delta)
                    continue

        return df

 

    def close(self):
        self.reqsession.close()
    
                            
if __name__=="__main__":
    pass
