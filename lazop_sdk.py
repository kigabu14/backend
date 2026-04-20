# -*- coding: utf-8 -*-
import requests, time, hmac, hashlib, json, logging, os, socket, platform
from os.path import expanduser

dir = expanduser("~")
os.makedirs(dir + "/logs", exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(dir + "/logs/lazopsdk.log." + time.strftime("%Y-%m-%d", time.localtime()))
handler.setLevel(logging.ERROR)
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

P_SDK_VERSION = "lazop-sdk-python-20181207"
P_APPKEY = "app_key"; P_ACCESS_TOKEN = "access_token"; P_TIMESTAMP = "timestamp"
P_SIGN = "sign"; P_SIGN_METHOD = "sign_method"; P_PARTNER_ID = "partner_id"
P_DEBUG = "debug"; P_CODE = 'code'; P_TYPE = 'type'; P_MESSAGE = 'message'; P_REQUEST_ID = 'request_id'

def sign(secret, api, parameters):
    sort_dict = sorted(parameters)
    parameters_str = "%s%s" % (api, str().join('%s%s' % (key, parameters[key]) for key in sort_dict))
    h = hmac.new(secret.encode("utf-8"), parameters_str.encode("utf-8"), digestmod=hashlib.sha256)
    return h.hexdigest().upper()

def mixStr(pstr):
    return pstr if isinstance(pstr, str) else str(pstr)

def logApiError(appkey, sdkVersion, requestUrl, code, message):
    localIp = socket.gethostbyname(socket.gethostname())
    logger.error("%s^_^%s^_^%s^_^%s^_^%s^_^%s^_^%s^_^%s" % (
        appkey, sdkVersion, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        localIp, platform.platform(), requestUrl, code, message))

class LazopRequest:
    def __init__(self, api_pame, http_method='POST'):
        self._api_params = {}; self._file_params = {}
        self._api_pame = api_pame; self._http_method = http_method
    def add_api_param(self, key, value): self._api_params[key] = value
    def add_file_param(self, key, value): self._file_params[key] = value

class LazopResponse:
    def __init__(self): self.type = self.code = self.message = self.request_id = self.body = None
    def __str__(self): return f"type={mixStr(self.type)} code={mixStr(self.code)} message={mixStr(self.message)}"

class LazopClient:
    log_level = "ERROR"
    def __init__(self, server_url, app_key, app_secret, timeout=30):
        self._server_url = server_url; self._app_key = app_key
        self._app_secret = app_secret; self._timeout = timeout

    def execute(self, request, access_token=None):
        sys_parameters = {
            P_APPKEY: self._app_key, P_SIGN_METHOD: "sha256",
            P_TIMESTAMP: str(int(round(time.time()))) + '000', P_PARTNER_ID: P_SDK_VERSION
        }
        if access_token: sys_parameters[P_ACCESS_TOKEN] = access_token
        sign_parameter = {**sys_parameters, **request._api_params}
        sign_parameter[P_SIGN] = sign(self._app_secret, request._api_pame, sign_parameter)
        api_url = "%s%s" % (self._server_url, request._api_pame)
        try:
            if request._http_method == 'POST' or len(request._file_params) != 0:
                r = requests.post(api_url, sign_parameter, files=request._file_params, timeout=self._timeout)
            else:
                r = requests.get(api_url, sign_parameter, timeout=self._timeout)
        except Exception as err:
            logApiError(self._app_key, P_SDK_VERSION, api_url, "HTTP_ERROR", str(err)); raise err
        response = LazopResponse()
        jsonobj = r.json()
        for attr in [P_CODE, P_TYPE, P_MESSAGE, P_REQUEST_ID]:
            if attr in jsonobj: setattr(response, attr.replace('request_id','request_id'), jsonobj[attr])
        response.code = jsonobj.get(P_CODE); response.type = jsonobj.get(P_TYPE)
        response.message = jsonobj.get(P_MESSAGE); response.request_id = jsonobj.get(P_REQUEST_ID)
        response.body = jsonobj
        return response
