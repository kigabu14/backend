"""
Lazada API Client — wraps official lazop SDK
API paths ตรงกับ Lazada Open Platform docs
"""
import json, time, hmac, hashlib, requests
from datetime import datetime, timedelta
from lazop_sdk import LazopClient, LazopRequest

GATEWAY_TH = "https://api.lazada.co.th/rest"
AUTH_URL   = "https://auth.lazada.com/rest"


def _sign_auth(app_secret, path, params):
    sorted_params = sorted(params.items())
    sign_str = path + "".join(str(k) + str(v) for k, v in sorted_params)
    return hmac.new(
        app_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


class LazadaClient:
    def __init__(self, app_key, app_secret, access_token=None):
        self.app_key      = app_key
        self.app_secret   = app_secret
        self.access_token = access_token
        self._sdk = LazopClient(GATEWAY_TH, app_key, app_secret)

    def _get(self, path, params=None):
        req = LazopRequest(path, "GET")
        for k, v in (params or {}).items():
            req.add_api_param(k, v)
        resp = self._sdk.execute(req, self.access_token)
        self._raise_if_error(resp)
        return resp.body.get("data", {})

    def _post(self, path, params=None):
        req = LazopRequest(path, "POST")
        for k, v in (params or {}).items():
            req.add_api_param(k, v)
        resp = self._sdk.execute(req, self.access_token)
        self._raise_if_error(resp)
        return resp.body.get("data", {})

    @staticmethod
    def _raise_if_error(resp):
        code = str(resp.code or "0")
        if code not in ("0", "200", "None", ""):
            friendly = {
                "6":     "order_item_ids format ผิด (ต้องเป็น integer)",
                "18":    "ต้องระบุ created_after หรือ updated_after",
                "24":    "Invalid Delivery Type",
                "30012": "ออเดอร์ยังไม่ได้ RTS",
            }.get(code, "")
            raise Exception(f"[{code}] {friendly or resp.message or 'Unknown error'}")

    @staticmethod
    def _clean_int_ids(raw_ids):
        ids = []
        for i in raw_ids:
            s = str(i).strip().strip('"').strip("'")
            try:    ids.append(int(s))
            except: ids.append(s)
        return ids

    # ═══════════════════════════════════════════════════════════════
    # ORDERS — /order/*
    # ═══════════════════════════════════════════════════════════════

    def get_orders(self, status="ready_to_ship", limit=100, offset=0, days=30):
        """GET /orders/get"""
        created_after = (datetime.utcnow() - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%S+00:00"
        )
        return self._get("/orders/get", {
            "status":         status,
            "limit":          limit,
            "offset":         offset,
            "sort_by":        "created_at",
            "sort_direction": "DESC",
            "created_after":  created_after,
        })

    def get_order_items(self, order_id):
        """GET /order/items/get"""
        result = self._get("/order/items/get", {"order_id": order_id})
        return result if isinstance(result, list) else []

    def get_shipping_providers(self, order_id):
        """GET /shipment/providers/get"""
        return self._get("/shipment/providers/get", {"order_id": order_id})

    def pack_order(self, order_item_ids, shipping_provider,
                   delivery_type="dropship", tracking_number=""):
        """POST /order/pack"""
        ids = self._clean_int_ids(order_item_ids)
        params = {
            "order_item_ids":    json.dumps(ids),
            "shipping_provider": shipping_provider,
            "delivery_type":     delivery_type,
        }
        if tracking_number:
            params["tracking_number"] = tracking_number
        return self._post("/order/pack", params)

    def get_document(self, order_item_ids, doc_type="shippingLabel"):
        """GET /order/document/get
        doc_type: shippingLabel | invoice | carton
        """
        ids = self._clean_int_ids(order_item_ids[:30])
        return self._get("/order/document/get", {
            "doc_type":       doc_type,
            "order_item_ids": json.dumps(ids),
        })

    # ═══════════════════════════════════════════════════════════════
    # REVERSE / RETURNS — /order/reverse/*
    # ═══════════════════════════════════════════════════════════════

    def get_reverse_return_list(self, start_time, end_time,
                                 page_size=40, page_number=1):
        """GET /order/reverse/return/detail/list
        ดึงรายละเอียดของคืนทั้งหมด (Reverse Order)

        Args:
            start_time:  "2025-01-01 00:00:00"
            end_time:    "2025-01-31 23:59:59"
            page_size:   max 40 ต่อหน้า
            page_number: เริ่มที่ 1
        """
        return self._get("/order/reverse/return/detail/list", {
            "start_time":  start_time,
            "end_time":    end_time,
            "page_size":   page_size,
            "page_number": page_number,
        })

    def update_reverse_return(self, reverse_order_line_id, status,
                               remark="", images=None):
        """POST /order/reverse/return/update
        อัปเดตสถานะการคืนสินค้า

        Args:
            reverse_order_line_id: ID ของรายการคืน
            status: REFUND_APPROVED | REFUND_REJECTED
            remark: หมายเหตุ
            images: list of image URLs (optional)
        """
        params = {
            "reverse_order_line_id": reverse_order_line_id,
            "status": status,
        }
        if remark:
            params["remark"] = remark
        if images:
            params["images"] = json.dumps(images)
        return self._post("/order/reverse/return/update", params)

    # ═══════════════════════════════════════════════════════════════
    # FINANCE — /finance/*
    # ═══════════════════════════════════════════════════════════════

    def get_payout_status(self, start_time, end_time):
        """GET /finance/payout/status/get"""
        return self._get("/finance/payout/status/get", {
            "start_time": start_time,
            "end_time":   end_time,
        })

    def query_transaction_details(self, start_time, end_time,
                                   trans_type="", page=1, page_size=100):
        """GET /finance/transaction/details/get   ← 's' ต่อท้าย details
        ดู transaction รายออเดอร์: ค่าคอม, ค่าขนส่ง, VAT, WHT

        trans_type options:
            Payment | Refund | Commission | Adjustment | LazCredit
        """
        params = {
            "start_time":  start_time,
            "end_time":    end_time,
            "page_number": page,
            "page_size":   page_size,
        }
        if trans_type:
            params["trans_type"] = trans_type
        return self._get("/finance/transaction/details/get", params)

    def query_account_transactions(self, start_time, end_time,
                                    page=1, page_size=100):
        """GET /finance/accounttransactions/get
        ดูยอดเงินเข้าออกบัญชีรวม
        """
        return self._get("/finance/accounttransactions/get", {
            "start_time":  start_time,
            "end_time":    end_time,
            "page_number": page,
            "page_size":   page_size,
        })

    # ═══════════════════════════════════════════════════════════════
    # PRODUCTS — /product/*
    # ═══════════════════════════════════════════════════════════════

    def get_products(self, status="active", limit=50, offset=0, search=""):
        """GET /products/get"""
        params = {"status": status, "limit": limit, "offset": offset}
        if search:
            params["search"] = search
        return self._get("/products/get", params)

    def update_price_quantity(self, skus):
        """POST /product/price_quantity/update   ← underscore ไม่ใช่ slash
        skus = [{"SellerSku": "xxx", "price": "100", "quantity": "10"}]
        """
        payload = json.dumps({
            "Request": {
                "Product": {
                    "Skus": {
                        "Sku": skus
                    }
                }
            }
        })
        return self._post("/product/price_quantity/update", {"payload": payload})

    def get_product_item(self, item_id=None, seller_sku=None):
        """GET /product/item/get
        ดูรายละเอียดสินค้า 1 รายการ
        """
        params = {}
        if item_id:    params["item_id"]    = item_id
        if seller_sku: params["seller_sku"] = seller_sku
        return self._get("/product/item/get", params)

    def create_product(self, payload_dict):
        """POST /product/create
        payload_dict = dict ตาม Lazada product schema
        """
        payload = json.dumps(payload_dict)
        return self._post("/product/create", {"payload": payload})

    def update_product(self, payload_dict):
        """POST /product/update
        แก้ไขชื่อ/รายละเอียด/รูปภาพสินค้า
        """
        payload = json.dumps(payload_dict)
        return self._post("/product/update", {"payload": payload})

    def upload_image(self, image_url):
        """POST /image/upload
        upload รูปจาก URL → คืน image hash สำหรับใช้ใน product
        """
        return self._post("/image/upload", {"url": image_url})

    def migrate_images(self, images_list):
        """POST /images/migrate
        migrate หลาย URL พร้อมกัน
        images_list = [{"url": "https://..."}]
        """
        return self._post("/images/migrate", {
            "images": json.dumps(images_list)
        })

    def get_category_tree(self):
        """GET /categories/tree/get"""
        result = self._get("/categories/tree/get")
        return result if isinstance(result, list) else []

    # ═══════════════════════════════════════════════════════════════
    # SYSTEM / FBI — /fbi/*
    # ═══════════════════════════════════════════════════════════════

    def fbi_start_export(self, dataset_name, start_time, end_time):
        """POST /fbi/download/startExportByDataset
        เริ่ม export ข้อมูลชุดใหญ่ (async) → คืน export_id

        dataset_name options (ตัวอย่าง):
            order | transaction | product_performance
        """
        return self._post("/fbi/download/startExportByDataset", {
            "dataset_name": dataset_name,
            "start_time":   start_time,
            "end_time":     end_time,
        })

    def fbi_get_export_status(self, export_id):
        """GET /fbi/download/getExportStatus
        เช็คสถานะ export job → คืน download_url เมื่อเสร็จ
        """
        return self._get("/fbi/download/getExportStatus", {
            "export_id": export_id,
        })

    # ═══════════════════════════════════════════════════════════════
    # AUTH
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def create_token(app_key, app_secret, code):
        params = {
            "app_key":     app_key,
            "timestamp":   str(int(round(time.time()))) + "000",
            "sign_method": "sha256",
            "code":        code,
        }
        params["sign"] = _sign_auth(app_secret, "/auth/token/create", params)
        resp = requests.get(AUTH_URL + "/auth/token/create",
                            params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") and str(data["code"]) != "0":
            raise Exception(f"[{data['code']}] {data.get('message','Token exchange failed')}")
        return data

    def refresh_access_token(self, refresh_token):
        params = {
            "app_key":       self.app_key,
            "timestamp":     str(int(round(time.time()))) + "000",
            "sign_method":   "sha256",
            "refresh_token": refresh_token,
        }
        params["sign"] = _sign_auth(self.app_secret, "/auth/token/refresh", params)
        resp = requests.get(AUTH_URL + "/auth/token/refresh",
                            params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
