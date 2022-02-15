import requests
import hmac, hashlib
import base64
import time
from datetime import datetime, timedelta

class Indx(object):
    stock_name = 'Indx'
#данные для входа

    def __init__(self, login, wmid, password, culture):
        self.login = login
        self.wmid = wmid
        self.password = password
        self.culture = culture

    # функции работы с биржей
    def get_balance(self):
        url = "https://api.indx.ru/api/v2/trade/Balance"  # get_balance
        payload_str = self.login + ';' + self.password + ';' + self.culture + ';' + self.wmid  # balance
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture, "Signature": self.get_signature(p_str=payload_str)}}
        result = self.call_api(req_body=req_body, url=url)
        return result

    def get_tools(self):
        url = "https://api.indx.ru/api/v2/trade/Tools"
        payload_str = self.login + ';' + self.password + ';' + self.culture # quote/base
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture, "Signature": self.get_signature(p_str=payload_str)}}
        result = self.call_api(req_body=req_body, url=url)
        return result

    def get_open_orders(self):
        url = "https://api.indx.ru/api/v2/trade/OfferMy"
        payload_str = self.login + ';' + self.password + ';' + self.culture + ';' + self.wmid  # get orders
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture,
                                   "Signature": self.get_signature(p_str=payload_str)}}
        #print(req_body)
        #print('test')
        result = self.call_api(req_body=req_body, url=url)
        return result

    def get_finished_orders(self, id):
        url = "https://api.indx.ru/api/v2/trade/HistoryTrading"
        datestart = "{:%Y%m%d}".format(datetime.now()-timedelta(86400))
        dateend = "{:%Y%m%d}".format(datetime.now()+timedelta(86400))
        payload_str = self.login + ';' + self.password + ';' + self.culture + ';' + self.wmid +";"+id + ";" +datestart +";"+dateend # get orders
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture,
                                   "Signature": self.get_signature(p_str=payload_str)},
                    "Trading":{"ID": id, "DateStart": datestart,"DateEnd": dateend}
                    }

        result = self.call_api(req_body=req_body, url=url)
        return result

    def create_order(self, id, count, isbid, price):
        url = "https://api.indx.ru/api/v2/trade/OfferAdd"
        payload_str = self.login + ';' + self.password + ';' + self.culture + ';' + self.wmid+';' + id  # set orders
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture,
                                   "Signature": self.get_signature(p_str=payload_str)},
                    "Offer": {"ID": id, "Count": count, "IsAnonymous": 'true', "IsBid": isbid, "Price": price}}

        result = self.call_api(req_body=req_body, url=url)
        return result

    def delete_order(self, order_id):
        url = "https://api.indx.ru/api/v2/trade/OfferDelete"
        payload_str = self.login + ';' + self.password + ';' + self.culture + ';' + self.wmid + ';' + order_id  # delete orders
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture, "Signature": self.get_signature(p_str=payload_str)},
                    "OfferId": order_id}
        result = self.call_api(req_body=req_body, url=url)
        return result

    def get_history(self, id):
        url = "https://api.indx.ru/api/v2/trade/tick"
        payload_str = self.login + ';' +self.password + ';' + self.culture + ';' + self.wmid + ';' + id + ';1'
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture, "Signature": self.get_signature(p_str=payload_str)},
                    "Tick": {"ID":id, "Kind":1}}
        result = self.call_api(req_body=req_body, url=url)
        return result

    def get_offers(self, id):
        url = "https://api.indx.ru/api/v2/trade/OfferList"
        payload_str = self.login + ';' +self.password + ';' + self.culture + ';' + self.wmid + ';' + id
        req_body = {"ApiContext": {"Login": self.login, "Wmid": self.wmid, "Culture": self.culture, "Signature": self.get_signature(p_str=payload_str)},
                    "Trading": {"ID":id}}
        result = self.call_api(req_body=req_body, url=url)


        return result

    def call_api(self, req_body, url):
        headers = {'Content-type': 'text/json', 'Accept': 'text/json'}
        res = requests.post(url, headers=headers, json=req_body, verify=True)
        #print(res.json())
        while res.json() == "Too many requests":
            time.sleep(2)
            res = requests.post(url, headers=headers, json=req_body, verify=True)

        #print(res.json())
        #time.sleep(2)
        return res.json()

    def get_signature(self,p_str):
        h = base64.b64encode(hashlib.new('sha256', p_str.encode('utf-8')).digest())
      #  h = base64.b64encode(hashlib.sha256(p_str.encode('utf-8')).digest())
        #print (str(h.decode('utf-8')))
        return (str(h.decode('utf-8')))

    #jeTXWmsMTcY2EVMnFBqWzC / m22zFgZHOQAl1OgIVyz0 =

