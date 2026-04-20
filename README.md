# Lazada Dashboard — Backend (Flask)

## Deploy บน Railway

1. ไปที่ https://railway.app → New Project → Deploy from local
2. Upload โฟลเดอร์นี้
3. แก้ไข config.json ใส่ credentials จริงของบอล
4. Railway จะ deploy อัตโนมัติ
5. Copy URL ของ Railway (เช่น https://lazada-backend.up.railway.app)
6. เปิด https://p2p-lazada-dashboard.netlify.app
7. กด ⚙️ Backend URL แล้วใส่ URL จาก Railway

## API Endpoints
- GET  /api/health                    — Health check
- GET  /api/orders/summary            — สรุปออเดอร์วันนี้
- GET  /api/orders?status=&days=      — รายการออเดอร์
- GET  /api/returns?days=             — รายการของคืน
- POST /api/returns/update            — อนุมัติ/ปฏิเสธคืน
- GET  /api/finance/summary?days=     — สรุปการเงิน
- GET  /api/finance/transactions?days= — รายการ transactions
- GET  /api/finance/payout?days=      — สถานะโอนเงิน
- GET  /api/products?status=          — รายการสินค้า
- POST /api/products/update           — อัปเดตราคา/สต็อก
- GET  /api/export/excel?days=        — Export Excel
- POST /api/fbi/export                — FBI Export (async)
- GET  /api/fbi/status?export_id=     — เช็คสถานะ FBI export
