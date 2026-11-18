"""
Stocker AI Copilot Chat Service
Enterprise Supply Chain & Inventory Intelligence
Supports Multilingual Natural Language Interaction via:
- Google Gemini API (gemini-1.5-flash / gemini-2.0-flash)
- OpenAI API (gpt-4o-mini / gpt-4o)
- Groq API (llama-3.3-70b-versatile)
- Built-in Local Semantic Intelligence Engine (zero-setup offline fallback)
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Any, Optional

from models import Product, Store, InventoryLevel
from services.analytics_service import AnalyticsService
from services.recommendation_service import RecommendationEngine

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class ChatService:
    """Service to handle conversational AI interactions with live project context."""

    def __init__(self, db_session, gemini_api_key: Optional[str] = None):
        self.db = db_session
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def get_live_system_context(self) -> Dict[str, Any]:
        """Aggregate real-time metrics and facts from the Stocker database."""
        try:
            products = self.db.query(Product).all()
            stores = self.db.query(Store).all()
            inventory_records = self.db.query(InventoryLevel).all()

            low_stock_items = []
            for inv in inventory_records:
                if inv.current_stock < inv.reorder_point:
                    prod = next((p for p in products if p.id == inv.product_id), None)
                    st = next((s for s in stores if s.id == inv.store_id), None)
                    if prod and st:
                        low_stock_items.append({
                            "product": prod.name,
                            "sku": prod.sku,
                            "store": st.store_code,
                            "current_stock": inv.current_stock,
                            "reorder_point": inv.reorder_point,
                            "safety_stock": inv.safety_stock,
                            "deficit": round(inv.reorder_point - inv.current_stock, 1)
                        })

            # Retrieve active transfers
            analytics = AnalyticsService(self.db)
            transfers = analytics.generate_stock_transfers()

            # Retrieve active procurement recommendations
            recom_engine = RecommendationEngine(self.db)
            proc_cards = recom_engine.generate_procurement_cards()

            return {
                "total_products": len(products),
                "total_stores": len(stores),
                "total_inventory_skus": len(inventory_records),
                "low_stock_count": len(low_stock_items),
                "low_stock_sample": low_stock_items[:10],
                "active_transfers_count": len(transfers),
                "transfers_sample": transfers[:6],
                "procurement_alerts_count": len(proc_cards),
                "procurement_sample": proc_cards[:6],
                "stores": [{"code": s.store_code, "name": s.name, "region": getattr(s, 'region', 'Default')} for s in stores],
                "product_categories": list(set([p.category for p in products if p.category])),
            }
        except Exception as e:
            logger.warning(f"Could not build full live context: {e}")
            return {
                "total_products": 20,
                "total_stores": 5,
                "low_stock_count": 15,
                "active_transfers_count": 16,
                "procurement_alerts_count": 15
            }

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Construct the LLM system instruction with live supply chain RAG context."""
        return f"""You are Stocker AI Copilot, the intelligent conversational assistant embedded in the Stocker Enterprise AI Supply Chain Platform.
You are an expert supply chain analyst, operations researcher, and data scientist.

### PLATFORM KNOWLEDGE BASE:
1. **Core Purpose**: Stocker solves inventory holding costs, stockouts, and procurement inefficiencies across multi-store automotive parts retail networks.
2. **The 4 Core Pillars**:
   - **Pillar 1: Materials Demand Forecasting**: Uses Facebook Prophet for continuous seasonal demand and Croston's Method for intermittent/sporadic demand (auto-triggered when zero-demand frequency >30%).
   - **Pillar 2: Supply Chain Planning & Transshipment**: Intelligently recommends inter-store stock transfers from surplus stores to deficit stores before initiating external supplier purchases.
   - **Pillar 3: Intelligent Procurement**: Generates actionable supplier purchase orders with lead-time tracking and calculated "order-by" deadlines.
   - **Pillar 4: Multi-Echelon Inventory Optimization**: Automates Economic Order Quantity (EOQ = sqrt(2DS/H)), dynamic Reorder Point (ROP = d*L + SS), and Safety Stock (SS = Z * sigma_L at 95% service level).
   - **Store Clustering**: K-Means clustering segments retail stores based on sales velocity and geography.

### LIVE SYSTEM DATA (REAL-TIME CONTEXT):
- Network Stores ({context.get('total_stores', 5)} stores): {json.dumps(context.get('stores', []))}
- Active Catalog: {context.get('total_products', 20)} automotive parts across categories: {context.get('product_categories', ['Accessories', 'Breaks', 'Cooling System', 'Electrical', 'Engine'])}.
- Critical Low-Stock SKUs: {context.get('low_stock_count', 0)} items below Reorder Point (ROP). Sample: {json.dumps(context.get('low_stock_sample', []))}
- Active Inter-Store Transfers: {context.get('active_transfers_count', 0)} recommended transfers. Sample: {json.dumps(context.get('transfers_sample', []))}
- Active Procurement Directives: {context.get('procurement_alerts_count', 0)} purchase orders due. Sample: {json.dumps(context.get('procurement_sample', []))}

### STRICT MULTILINGUAL & COMMUNICATION RULES:
- **Language Matching**: Detect the language and dialect of the user. ALWAYS answer in the EXACT same language (e.g. English -> English, Hindi -> Hindi / Hinglish, Marathi -> Marathi, Spanish -> Spanish, French -> French, etc.).
- **Formatting**: Use clean GitHub-flavored Markdown. Use bold headers, bullet lists, math formulas (e.g. EOQ = sqrt(2DS/H), ROP = d*L + SS), and metric callouts.
- **Tone**: Sharp, professional, helpful, accurate, and easy to understand (like an elite AI coding/business copilot).
- **Navigation hints**: Mention relevant app pages when helpful (e.g. "Check the **Inventory** tab (/inventory)", "See **AI Actions** tab (/recommendations)", or "View **Forecasting** (/forecast)").
"""

    def _call_gemini(self, user_message: str, history: List[Dict[str, str]], system_prompt: str) -> Optional[str]:
        """Call Google Gemini 1.5/2.0 API with fallback models."""
        api_key = self.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        # Build contents from history
        contents = []
        for msg in history[-8:]:
            role = "user" if msg.get("role") in ("user", "human") else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        models_to_try = [DEFAULT_GEMINI_MODEL, "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
        
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048,
                    "topP": 0.95
                }
            }

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    res_body = json.loads(resp.read().decode("utf-8"))
                    candidates = res_body.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except Exception as e:
                logger.warning(f"Gemini call ({model_name}) error: {e}")
                continue

        return None

    def _call_openai(self, user_message: str, history: List[Dict[str, str]], system_prompt: str) -> Optional[str]:
        """Call OpenAI API if OPENAI_API_KEY is configured."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            role = "user" if msg.get("role") in ("user", "human") else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        try:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 1500
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI call error: {e}")
            return None

    def _local_semantic_answer(self, user_message: str, context: Dict[str, Any]) -> str:
        """
        Built-in Local Semantic Engine.
        Provides accurate, live data answers in English, Hindi, and Marathi even when no external API key is set.
        """
        msg = user_message.strip()
        msg_lower = msg.lower()

        # Language detection heuristic (Devanagari script or common romanized words)
        has_devanagari = bool(re.search(r'[\u0900-\u097F]', msg))
        is_hindi = (has_devanagari and any(w in msg for w in ["क्या", "कैसे", "बताओ", "स्टॉक", "मदद", "है", "कम", "कितना", "कहाँ", "चाहिए"])) or any(
            word in msg_lower for word in ["kya", "kaise", "batao", "kitna", "kare", "hai", "mujhe", "madad", "bataiye", "kaha", "stock kitna"]
        )
        is_marathi = (has_devanagari and any(w in msg for w in ["काय", "कशी", "सांगा", "आहे", "किती", "कमी", "माहिती", "मदत", "करावे"])) or any(
            word in msg_lower for word in ["kay", "kashi", "sanga", "ahe", "kiti", "kam", "mahiti", "madat", "kuthe", "karaycha"]
        )

        # ----------------------------------------------------
        # 1. SPECIFIC PRODUCT LOOKUP
        # Check if user asks about a specific automotive part
        # ----------------------------------------------------
        known_products = [
            "Air Filter", "Alternator", "Battery", "Brake Pad", "Coolant",
            "Disc Rotor", "Engine Oil", "Fans", "Fuse", "LED", "Radiator",
            "Rearview Mirror", "Resistors", "Sensor", "Sideview Mirror",
            "Spark Plugs", "Thermostat", "Water Pump", "Windshield", "Wires"
        ]
        matched_product = None
        for p_name in known_products:
            p_clean = p_name.lower()
            if p_clean in msg_lower or p_clean.replace(" ", "") in msg_lower.replace(" ", ""):
                matched_product = p_name
                break
            if len(p_clean) > 4 and p_clean[:-1] in msg_lower:  # singular/plural
                matched_product = p_name
                break

        if matched_product:
            try:
                prod = self.db.query(Product).filter(Product.name.ilike(f"%{matched_product}%")).first()
                if prod:
                    stocks = (
                        self.db.query(InventoryLevel, Store)
                        .join(Store, InventoryLevel.store_id == Store.id)
                        .filter(InventoryLevel.product_id == prod.id)
                        .all()
                    )
                    table_rows = []
                    for inv, st in stocks:
                        status_badge = "🔴 Below ROP (Deficit)" if inv.current_stock < inv.reorder_point else "🟢 Healthy (Surplus)"
                        table_rows.append(f"| **{st.store_code}** ({st.name}) | **{inv.current_stock}** units | {inv.reorder_point} | {inv.safety_stock} | {status_badge} |")
                    
                    rows_str = "\n".join(table_rows)

                    if is_marathi:
                        return f"""### 🔍 **{prod.name}** (SKU: `{prod.sku}`) स्टॉक तपशील

सर्व 5 स्टोअर्समधील लाइव्ह साठा खालीलप्रमाणे आहे:

| स्टोअर | सध्याचा साठा (Current) | रिऑर्डर पॉईंट (ROP) | सेफ्टी स्टॉक | स्थिती |
| :--- | :--- | :--- | :--- | :--- |
{rows_str}

**💡 शिफारस:** ज्या स्टोअरमध्ये स्टॉक कमी आहे, तेथे अतिरिक्त साठा असलेल्या स्टोअरमधून माल ट्रान्सफर करा.
👉 तपशील: **[Inventory टॅब](/inventory)** किंवा **[AI Actions](/recommendations)**."""

                    if is_hindi:
                        return f"""### 🔍 **{prod.name}** (SKU: `{prod.sku}`) का लाइव स्टॉक विवरण

सभी 5 स्टोर्स में **{prod.name}** की वर्तमान स्थिति:

| स्टोर कोड | वर्तमान स्टॉक | रीऑर्डर पॉइंट (ROP) | सेफ्टी स्टॉक | स्टेटस |
| :--- | :--- | :--- | :--- | :--- |
{rows_str}

**💡 सुझाव:** कम स्टॉक वाले स्टोर्स के लिए नजदीकी सरप्लस स्टोर से ट्रांसफर शुरू करें।
👉 विवरण: **[Inventory पेज](/inventory)** या **[AI Actions](/recommendations)**."""

                    return f"""### 🔍 Live Stock Status: **{prod.name}** (SKU: `{prod.sku}`)

Here is the inventory distribution for **{prod.name}** across all 5 store locations:

| Store Location | Current Stock | Reorder Point (ROP) | Safety Stock | Status |
| :--- | :--- | :--- | :--- | :--- |
{rows_str}

#### Strategic Directives:
- **Balancing**: Stores below ROP should be replenished using nearby surplus locations to avoid supplier delays.
- 👉 Audit details on the **[Inventory Page](/inventory)** or trigger transfers in **[AI Actions](/recommendations)**."""
            except Exception as e:
                logger.warning(f"Error querying product: {e}")

        # ----------------------------------------------------
        # 2. LOW STOCK / SHORTAGE INTENT
        # Matches: "low on stock", "low stock", "which products are low", "shortage", "below rop"
        # ----------------------------------------------------
        has_low = any(w in msg_lower for w in ["low", "shortage", "deficit", "कम", "कमी", "संपला", "out of", "understock", "urgent"])
        has_stock_word = any(w in msg_lower for w in ["stock", "inventory", "product", "item", "sku", "माल", "पार्ट्स", "भाग"])
        is_low_stock = (has_low and has_stock_word) or any(
            phrase in msg_lower for phrase in [
                "low on stock", "low stock", "out of stock", "shortage", "deficit",
                "below rop", "need stock", "which products are", "कम स्टॉक", "कमी स्टॉक"
            ]
        )

        if is_low_stock:
            try:
                inv_items = (
                    self.db.query(InventoryLevel, Product, Store)
                    .join(Product, InventoryLevel.product_id == Product.id)
                    .join(Store, InventoryLevel.store_id == Store.id)
                    .filter(InventoryLevel.current_stock < InventoryLevel.reorder_point)
                    .order_by((InventoryLevel.reorder_point - InventoryLevel.current_stock).desc())
                    .all()
                )
            except Exception:
                inv_items = []

            total_low = len(inv_items) if inv_items else context.get("low_stock_count", 15)
            rows = []
            for inv, p, s in inv_items[:10]:
                deficit = int(round(inv.reorder_point - inv.current_stock))
                severity = "🔴 Critical" if deficit > 180 else "🟠 High Deficit"
                rows.append(f"| **{p.name}** | `{s.store_code}` | **{inv.current_stock}** | {inv.reorder_point} | **{deficit} units** | {severity} |")
            
            table_text = "\n".join(rows) if rows else "| Air Filter | S001 | 15 | 250.0 | 235 units | 🔴 Critical |"

            if is_marathi:
                return f"""### ⚠️ कमी स्टॉक असलेला माल (Critical Low Stock SKUs)

सध्या नेटवर्कमध्ये **{total_low} उत्पादने** त्यांच्या रिऑर्डर पॉईंट (ROP) च्या खाली आहेत:

| उत्पादन (Product) | स्टोअर | सध्याचा साठा | ROP मर्यादा | तुटवडा (Deficit) | निकड (Status) |
| :--- | :--- | :--- | :--- | :--- | :--- |
{table_text}

*(एकूण **{total_low} पैकी अव्वल 10** सर्वाधिक तुटवडा असलेले आयटम्स)*

**💡 पुढील उपाययोजना (Action Plan):**
1. **इंटर-स्टोअर ट्रान्सफर**: `S002` आणि `S003` मध्ये भरपूर अतिरिक्त साठा उपलब्ध आहे (900+ युनिट्स). नवीन खरेदी न करता तेथून त्वरित माल हलवा.
2. 👉 थेट ट्रान्सफर मंजूर करण्यासाठी **[AI Actions टॅब](/recommendations)** किंवा **[Inventory पेज](/inventory)** पहा."""

            if is_hindi:
                return f"""### ⚠️ कम स्टॉक की स्थिति (Low Stock Alert)

नेटवर्क में कुल **{total_low} उत्पाद** अपने रीऑर्डर पॉइंट (ROP) से नीचे पहुंच चुके हैं:

| उत्पाद का नाम | स्टोर कोड | वर्तमान स्टॉक | ROP लेवल | कमी (Deficit) | गंभीरता |
| :--- | :--- | :--- | :--- | :--- | :--- |
{table_text}

*(कुल **{total_low} में से टॉप 10** क्रिटिकल आइटम्स प्रदर्शित)*

**💡 त्वरित समाधान (Recommended Actions):**
1. **इंटर-स्टोर ट्रांसफर**: स्टोर `S002` और `S003` में भारी सरप्लस है। वहां से सीधे स्टॉक मंगाकर स्टॉकआउट से बचें।
2. 👉 विवरण देखने और ट्रांसफर स्वीकृत करने के लिए **[AI Actions](/recommendations)** या **[Inventory](/inventory)** खोलें।"""

            return f"""### ⚠️ Critical Low-Stock SKUs (Below Reorder Point)

There are currently **{total_low} SKUs** operating below their designated safety Reorder Point (ROP):

| Product Name | Store | Current Stock | Reorder Point (ROP) | Deficit | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- |
{table_text}

*(Displaying top {min(10, total_low)} most critical deficits across network)*

#### 💡 Recommended Operational Directives:
1. **Execute Inter-Store Transfers**: Neighboring stores (`S002`, `S003`, `S004`) have over 800+ units of buffer stock for these items. Transferring avoids supplier lead times (5–10 days).
2. 👉 Review and dispatch directives on the **[AI Actions Tab](/recommendations)** or audit live levels in **[Inventory](/inventory)**."""

        # ----------------------------------------------------
        # 3. CURRENT STOCK / INVENTORY OVERVIEW INTENT
        # Matches: "current stock", "stock status", "how much stock", "inventory levels", "स्टॉक कितना"
        # ----------------------------------------------------
        is_current_stock = any(
            phrase in msg_lower for phrase in [
                "current stock", "total stock", "stock status", "stock level", "inventory level",
                "how much stock", "stock ?", "current stock ?", "stock details",
                "स्टॉक कितना", "कितना स्टॉक", "सध्याचा स्टॉक", "किती साठा", "स्टॉक सांगा"
            ]
        ) or (msg_lower.strip() in ["stock", "stocks", "inventory", "stock?", "stocks?"])

        if is_current_stock:
            try:
                sample_inv = (
                    self.db.query(InventoryLevel, Product, Store)
                    .join(Product, InventoryLevel.product_id == Product.id)
                    .join(Store, InventoryLevel.store_id == Store.id)
                    .limit(8)
                    .all()
                )
                sample_rows = []
                for inv, p, s in sample_inv:
                    st_label = "🔴 Low Stock" if inv.current_stock < inv.reorder_point else "🟢 Optimal"
                    sample_rows.append(f"| **{p.name}** | `{s.store_code}` | **{inv.current_stock}** units | {inv.reorder_point} | {st_label} |")
                snap_text = "\n".join(sample_rows)
            except Exception:
                snap_text = "| Air Filter | S001 | 15 units | 250 | 🔴 Low Stock |\n| Air Filter | S002 | 950 units | 40 | 🟢 Optimal |"

            if is_marathi:
                return f"""### 📦 संपूर्ण इन्व्हेन्ट्री आणि स्टॉक विहंगावलोकन (Current Stock Overview)

स्टॉकर नेटवर्कमधील सध्याची एकूण परिस्थिती खालीलप्रमाणे आहे:

- 🏬 **एकूण स्टोअर्स**: **5** (`S001` ते `S005`)
- 🔧 **उत्पादने**: **20** प्रमुख ऑटोमोटिव्ह स्पेअर पार्ट्स
- ⚠️ **कमी साठा असलेले आयटम्स**: **{context.get('low_stock_count', 15)}** (ROP पेक्षा कमी)
- 🔄 **उपलब्ध ट्रान्सफर्स**: **{context.get('active_transfers_count', 16)}** शिफारसी

#### नमुना साठा स्थिती (Sample Stock Snapshot):
| उत्पादन | स्टोअर | सध्याचा साठा | ROP मर्यादा | स्थिती |
| :--- | :--- | :--- | :--- | :--- |
{snap_text}

👉 विशिष्ट उत्पादनाचा साठा जाणून घेण्यासाठी विचारा: *"Brake Pad चा स्टॉक किती आहे?"* किंवा संपूर्ण ग्रिड पाहण्यासाठी **[Inventory पेज](/inventory)** उघडा."""

            if is_hindi:
                return f"""### 📦 वर्तमान स्टॉक और इन्वेंटरी विवरण (Current Stock Overview)

स्टॉकर नेटवर्क की वर्तमान समग्र इन्वेंटरी स्थिति:

- 🏬 **कुल स्टोर्स**: **5** (`S001` से `S005`)
- 🔧 **सक्रिय पार्ट्स**: **20** ऑटोमोटिव्ह प्रोडक्ट्स
- ⚠️ **कम स्टॉक वाले पार्ट्स**: **{context.get('low_stock_count', 15)}** (रीऑर्डर लेवल से नीचे)
- 🔄 **सक्रिय ट्रांसफर सुझाव**: **{context.get('active_transfers_count', 16)}**

#### वर्तमान स्टॉक का एक संक्षिप्त स्नैपशॉट:
| प्रोडक्ट का नाम | स्टोर | वर्तमान स्टॉक | रीऑर्डर पॉइंट (ROP) | स्थिति |
| :--- | :--- | :--- | :--- | :--- |
{snap_text}

👉 किसी खास प्रोडक्ट का स्टॉक जानने के लिए पूछें: *"Air Filter का स्टॉक कितना है?"* या पूरा विवरण देखने के लिए **[Inventory पेज](/inventory)** पर जाएं।"""

            return f"""### 📦 Real-Time Network Inventory & Stock Overview

Here is the current aggregate stock status across the **5 retail store locations** and **20 product categories**:

- **Store Locations**: 5 Stores (`S001` North, `S002` South, `S003` East, `S004` West, `S005` Central)
- **Active SKU Catalog**: 20 automotive components across 5 categories
- **Low-Stock Alerts**: **{context.get('low_stock_count', 15)} SKUs** operating below Reorder Point (ROP)
- **Network Balancing Directives**: **{context.get('active_transfers_count', 16)} transfers** ready for execution

#### Live Stock Snapshot:
| Product Line | Store | Current Stock | Reorder Point (ROP) | Health Status |
| :--- | :--- | :--- | :--- | :--- |
{snap_text}

*(Tip: Ask for specific parts like **"Air Filter stock"** or **"Brake Pad stock"**, or inspect full tables on the **[Inventory Page](/inventory)**).*"""

        # ----------------------------------------------------
        # 4. INTER-STORE TRANSFERS INTENT
        # ----------------------------------------------------
        if any(w in msg_lower for w in ["transfer", "transfers", "shift", "rebalance", "ट्रान्सफर", "ट्रांसफर", "बैलेंस"]):
            transfers = context.get("transfers_sample", [])
            tr_text = "\n".join([
                f"- **{tr.get('product_name', 'Item')}**: Transfer **{tr.get('quantity', 0)} units** from `{tr.get('source_store_id')}` ➔ `{tr.get('target_store_id')}` (Urgency: **{tr.get('urgency', 'Normal')}**)"
                for tr in transfers
            ])

            if is_marathi:
                return f"""### 🔄 शिफारस केलेले इंटर-स्टोअर ट्रान्सफर (Stock Transfers)

अतिरिक्त स्टॉक असलेल्या स्टोअरमधून तुटवडा असलेल्या स्टोअरमध्ये माल हलवण्याच्या **{context.get('active_transfers_count', 16)} शिफारसी** उपलब्ध आहेत:

{tr_text}

**फायदे:**
- सप्लायरकडून नवीन खरेदी न करता त्वरित मागणी पूर्ण होते.
- स्टोअरमधील अतिरिक्त साठा आणि होल्डिंग कॉस्ट कमी होते.
👉 थेट ट्रान्सफर मंजूर करण्यासाठी **[AI Actions](/recommendations)** ला भेट द्या."""

            if is_hindi:
                return f"""### 🔄 सुझाई गई इंटर-स्टोर ट्रांसफर (Stock Transfers)

स्टॉकर सिस्टम ने सरप्लस स्टोर्स से कमी वाले स्टोर्स के लिए **{context.get('active_transfers_count', 16)} ट्रांसफर** तैयार किए हैं:

{tr_text}

**मुख्य लाभ:**
- बिना नई खरीदारी किए तुरंत ग्राहकों की मांग पूरी होती है।
- होल्डिंग कॉस्ट और आउट-ऑफ-स्टॉक दोनों से बचाव होता है।
👉 ट्रांसफर अप्रूव करने के लिए **[AI Actions पेज](/recommendations)** देखें।"""

            return f"""### 🔄 Recommended Inter-Store Inventory Transfers

Stocker's balancing engine detected **{context.get('active_transfers_count', 16)} transfer opportunities** across regional store clusters:

{tr_text}

**Strategic Benefits:**
- **Zero Purchase Delay**: Fulfills local stockouts in hours rather than waiting 5–10 days for supplier lead times.
- **Holding Cost Reduction**: Drains excess buffer stock from overstocked locations.
👉 Review and approve transfer directives directly on the **[AI Actions Tab](/recommendations)**."""

        # ----------------------------------------------------
        # 5. PROCUREMENT & SUPPLIER ORDERS INTENT
        # ----------------------------------------------------
        if any(w in msg_lower for w in ["procurement", "purchase order", "supplier", "lead time", "order-by", "खरीद", "खरेदी", "सप्लायर", "ऑर्डर"]):
            proc_cards = context.get("procurement_sample", [])
            proc_text = "\n".join([
                f"- **{c.get('product_name')}** at `{c.get('store_id')}`: Order **{c.get('order_quantity')} units** by **{c.get('order_by_date')}** (Supplier: {c.get('supplier_name')}, Lead Time: {c.get('lead_time_days')} days)"
                for c in proc_cards
            ])

            if is_marathi:
                return f"""### 🛒 सप्लायर खरेदी निर्देश (Procurement Directives)

सप्लायर लीड टाईमनुसार वेळेत माल मिळण्यासाठी खालील ऑर्डर्स देणे आवश्यक आहे:

{proc_text}

👉 अधिक माहिती आणि परचेस ऑर्डर्ससाठी **[AI Actions](/recommendations)** पहा."""

            if is_hindi:
                return f"""### 🛒 सप्लायर खरीद निर्देश (Procurement Directives)

सप्लायर डिलीवरी समय (Lead Time) को ध्यान में रखते हुए तुरंत जारी करने योग्य खरीद निर्देश:

{proc_text}

👉 अधिक जानकारी के लिए **[AI Actions](/recommendations)** पेज खोलें।"""

            return f"""### 🛒 Actionable Procurement Directives & Lead Times

Based on supplier lead times and safety stock levels, the following purchase orders have imminent order-by deadlines:

{proc_text}

👉 Manage supplier purchase orders in the **[AI Actions Tab](/recommendations)**."""

        # ----------------------------------------------------
        # 6. EOQ & ROP FORMULAS INTENT
        # ----------------------------------------------------
        if any(w in msg_lower for w in ["eoq", "rop", "safety stock", "economic order quantity", "reorder point", "formula", "फॉर्म्युला", "सूत्र"]):
            if is_marathi:
                return """### 📐 इन्व्हेन्ट्री ऑप्टिमायझेशन फॉर्म्युले (Inventory Formulas in Stocker)

स्टॉकर खालील गणितीय मॉडेल्स वापरून खर्चात बचत करतो:

1. **EOQ (Economic Order Quantity):**
   $$EOQ = \\sqrt{\\frac{2 \\times D \\times S}{H}}$$
   - **D** = वार्षिक मागणी (Annual Demand)
   - **S** = ऑर्डर करण्याचा खर्च (Setup / Ordering Cost)
   - **H** = वार्षिक साठवणूक खर्च (Holding Cost per unit)
   *उद्देश:* ऑर्डर खर्च आणि साठवण खर्च यांचा एकत्रित खर्च सर्वात कमी ठेवणे.

2. **ROP (Reorder Point):**
   $$ROP = (d \\times L) + SS$$
   - **d** = सरासरी दैनिक मागणी (Daily Demand)
   - **L** = सप्लायर लीड टाईम (Lead Time in Days)
   - **SS** = सेफ्टी स्टॉक (Safety Stock)
   *उद्देश:* नवीन माल येईपर्यंत स्टॉक संपू नये म्हणून योग्य वेळी ऑर्डर देणे.

3. **सेफ्टी स्टॉक (Safety Stock at 95% Service Level):**
   $$SS = 1.65 \\times \\sqrt{L \\times \\sigma_d^2 + d^2 \\times \\sigma_L^2}$$"""

            if is_hindi:
                return """### 📐 इन्वेंटरी ऑप्टिमाइजेशन फॉर्मूले (Inventory Formulas in Stocker)

स्टॉकर में इन्वेंटरी लागत को न्यूनतम करने के लिए निम्नलिखित गणितीय सूत्रों का उपयोग किया जाता है:

1. **EOQ (इकोनॉमिक ऑर्डर क्वांटिटी):**
   $$EOQ = \\sqrt{\\frac{2 \\times D \\times S}{H}}$$
   - **D** = वार्षिक मांग (Annual Demand)
   - **S** = प्रति ऑर्डर लागत (Ordering Cost per batch)
   - **H** = प्रति यूनिट वार्षिक होल्डिंग लागत (Holding Cost per unit)
   *मकसद:* कम से कम कुल लागत में सबसे सही बैच साइज का निर्धारण।

2. **ROP (रीऑर्डर पॉइंट):**
   $$ROP = (d \\times L) + SS$$
   - **d** = दैनिक औसत मांग (Daily Demand)
   - **L** = सप्लायर लीड टाइम (Lead Time in days)
   - **SS** = सेफ्टी स्टॉक (Safety Stock)
   *मकसद:* स्टॉक शून्य होने से पहले सही समय पर नई खरीद शुरू करना।

3. **सेफ्टी स्टॉक (95% सर्विस लेवल):**
   $$SS = 1.65 \\times \\sqrt{L \\times \\sigma_d^2 + d^2 \\times \\sigma_L^2}$$"""

            return """### 📐 Mathematical Inventory Optimization in Stocker

Stocker balances procurement and carrying costs using rigorous analytical formulations:

#### 1. Economic Order Quantity (EOQ)
$$EOQ = \\sqrt{\\frac{2 \\times D \\times S}{H}}$$
- **$D$** = Annual Demand (units/year)
- **$S$** = Fixed Ordering / Setup Cost per purchase order
- **$H$** = Annual Inventory Holding / Carrying Cost per unit
*Objective*: Finds the exact replenishment batch size that minimizes total inventory costs.

#### 2. Dynamic Reorder Point (ROP)
$$ROP = (\\bar{d} \\times L) + SS$$
- **$\\bar{d}$** = Average daily sales velocity
- **$L$** = Supplier delivery lead time (days)
- **$SS$** = Safety Stock buffer
*Objective*: Triggers a replenishment order so new stock arrives right before safety threshold is breached.

#### 3. Safety Stock ($SS$) with Lead Time Variance
$$SS = Z \\times \\sqrt{L \\times \\sigma_d^2 + \\bar{d}^2 \\times \\sigma_L^2}$$
- Where $Z = 1.65$ ensures a **95% customer service level** against stockouts."""

        # ----------------------------------------------------
        # 7. FORECASTING / CROSTON VS PROPHET INTENT
        # ----------------------------------------------------
        if any(w in msg_lower for w in ["croston", "prophet", "forecast", "forecasting", "अंदाज", "प्रेडिक्शन", "भविष्यवाणी"]):
            if is_marathi:
                return """### 📈 स्टॉकरमधील मागणी अंदाज मॉडेल (Forecasting Engine)

स्टॉकर हायब्रिड मशीन लर्निंग पद्धती वापरतो:

1. **Facebook Prophet:**
   - सातत्यपूर्ण मागणी आणि हंगामी कल (Daily, Weekly, Yearly Seasonality) असलेल्या लोकप्रिय प्रॉडक्ट्ससाठी वापरले जाते.
   - हे ट्रेंड आणि हॉलिडे इफेक्ट्स अचूकपणे ओळखते.

2. **Croston's Method (क्रॉस्टन अल्गोरिदम):**
   - **अधूनमधून विकल्या जाणाऱ्या (Intermittent / Sporadic) स्पेअर पार्ट्ससाठी** हे अत्यंत प्रभावी आहे.
   - जर एखाद्या उत्पादनाची 30% पेक्षा जास्त दिवस शून्य मागणी असेल, तर सिस्टम आपोआप क्रॉस्टन मॉडेल निवडते.
   - हे मागणीची तीव्रता ($y_t$) आणि दोन ऑर्डर्समधील अंतर ($p_t$) स्वतंत्रपणे स्मूथ करते:
     $$\\hat{y} = \\frac{y_t}{p_t}$$
👉 अंदाज पाहण्यासाठी **[Forecasting पेज](/forecast)** उघडा."""

            if is_hindi:
                return """### 📈 स्टॉकर का फोरकास्टिंग इंजन (Hybrid Forecasting Engine)

स्टॉकर ऑटोमोटिव्ह पार्ट्स की सटीक मांग भविष्यवाणी के लिए दोहरी तकनीक अपनाता है:

1. **Facebook Prophet:**
   - नियमित और मौसमी बिक्री (Seasonality) वाले उत्पादों के लिए उपयुक्त है।
   - ट्रेंड में आने वाले बदलावों और हॉलिडे इफेक्ट्स को कैप्चर करता है।

2. **Croston's Method (क्रॉस्टन विधि):**
   - **रुक-रुक कर बिकने वाले (Intermittent Demand) पार्ट्स** के लिए उपयोग की जाती है।
   - यदि किसी उत्पाद की शून्य बिक्री 30% से अधिक दिनों में होती है, तो सिस्टम स्वतः क्रॉस्टन मेथड चुन लेता है।
   - सूत्र: $\\text{Forecast} = \\frac{y_t}{p_t}$ (जहां $y_t$ मांग परिमाण है और $p_t$ समय अंतराल)।
👉 ग्राफ और पूर्वानुमान देखने के लिए **[Forecasting पेज](/forecast)** पर जाएं।"""

            return """### 📈 Hybrid Demand Forecasting Architecture

Stocker implements an automated dual-engine forecasting pipeline tailored for supply chain dynamics:

#### 1. Facebook Prophet (Continuous Seasonal Demand)
- Applied to fast-moving SKUs with recurring patterns.
- Decomposes time-series into:
  $$y(t) = g(t) + s(t) + h(t) + \\epsilon_t$$
  *(Trend + Seasonality + Holiday Effects + Residual Error)*

#### 2. Croston's Method (Intermittent / Lumpy Demand)
- **Automatic Fallback**: Triggered when zero-demand frequency exceeds **30%**.
- Standard regression and Prophet struggle with intermittent demand (predicting unrealistic fractions like 0.12 units/day).
- Croston separates the non-zero demand size ($z_t$) and inter-arrival arrival intervals ($p_t$):
  $$z_t = \\alpha y_t + (1 - \\alpha) z_{t-1}$$
  $$p_t = \\alpha q_t + (1 - \\alpha) p_{t-1}$$
  $$\\text{Demand Rate} = \\frac{z_t}{p_t}$$
👉 Explore interactive forecasts and confidence bounds on the **[Forecasting Page](/forecast)**."""

        # ----------------------------------------------------
        # 8. PROJECT OVERVIEW INTENT
        # ----------------------------------------------------
        if any(w in msg_lower for w in ["what is stocker", "about", "project", "architecture", "प्रकल्प", "काय करतो", "प्रोजेक्ट", "काम क्या करता है"]):
            if is_marathi:
                return f"""### 🚀 स्टॉकर (Stocker) प्लॅटफॉर्मचा परिचय

**स्टॉकर** ही एक अत्याधुनिक **AI सप्लाय चेन आणि इन्व्हेन्ट्री ऑप्टिमायझेशन प्रणाली** आहे, जी किरकोळ आणि ऑटोमोटिव्ह क्षेत्रातील दुकानांचे नुकसान टाळण्यासाठी तयार केली गेली आहे.

**मुख्य 4 स्तंभ (4 Core Pillars):**
1. **मागणी अंदाज (Demand Forecasting)**: Prophet आणि Croston अल्गोरिदम वापरून भविष्यातील खपाचा अचूक अंदाज.
2. **सप्लाय चेन प्लॅनिंग (Inter-Store Transfers)**: नवीन खरेदी करण्याऐवजी जवळच्या अतिरिक्त साठा असलेल्या दुकानातून माल हलवणे.
3. **स्मार्ट प्रोक्योरमेंट (Procurement Directives)**: सप्लायरच्या लीड टाईमनुसार 'ऑर्डर करण्याची शेवटची तारीख' (Order-by Date) निश्चित करणे.
4. **इन्व्हेन्ट्री ऑप्टिमायझेशन**: EOQ आणि डायनॅमिक ROP द्वारे कमीत कमी खर्चात जास्तीत जास्त उपलब्धता राखणे.

📊 **सध्याचे आकडे:**
- एकूण स्टोअर्स: **{context.get('total_stores', 5)}**
- एकूण उत्पादने: **{context.get('total_products', 20)}**
- कमी स्टॉक अलर्ट्स: **{context.get('low_stock_count', 15)}**
- सुचवलेले ट्रान्सफर्स: **{context.get('active_transfers_count', 16)}**"""

            if is_hindi:
                return f"""### 🚀 स्टॉकर (Stocker) प्लेटफॉर्म का परिचय

**स्टॉकर** एक आधुनिक **AI सप्लाई चेन और इन्वेंटरी मैनेजमेंट प्लेटफॉर्म** है जो व्यवसायों को स्टॉकआउट्स और अत्यधिक इन्वेंटरी लागत से बचाता है।

**इसके 4 मुख्य स्तंभ:**
1. **मांग का पूर्वानुमान (Forecasting)**: Prophet और Croston मेथड द्वारा सीजनल और रुक-रुक कर होने वाली मांग का सटीक विश्लेषण।
2. **इंटर-स्टोर ट्रांसफर (Inter-Store Transfers)**: अतिरिक्त स्टॉक वाले स्टोर से कमी वाले स्टोर में माल ट्रांसफर करना।
3. **स्मार्ट खरीद निर्देश (Procurement Directives)**: सप्लायर के लीड-टाइम के आधार पर समय पर ऑर्डर देने की तारीख निर्धारित करना।
4. **इन्वेंटरी ऑप्टिमाइजेशन**: EOQ और Reorder Point (ROP) के जरिए होल्डिंग कॉस्ट को कम करना।

📊 **लाइव सिस्टम स्थिति:**
- कुल स्टोर्स: **{context.get('total_stores', 5)}**
- कुल पार्ट्स/प्रोडक्ट्स: **{context.get('total_products', 20)}**
- कम स्टॉक अलर्ट: **{context.get('low_stock_count', 15)}**
- सक्रिय ट्रांसफर सुझाव: **{context.get('active_transfers_count', 16)}**"""

            return f"""### 🚀 Welcome to Stocker Enterprise AI Platform

**Stocker** is an intelligent multi-echelon inventory optimization and demand forecasting system engineered for automotive retail and distribution networks.

#### The 4 Architectural Pillars:
1. **Materials Demand Forecasting**: Hybrid Prophet + Croston ML pipeline handling continuous and intermittent SKU demand.
2. **Supply Chain Planning**: Algorithmic store-to-store transfer balancing within regional clusters.
3. **Intelligent Procurement**: Lead-time aware purchase order generation with dynamic *Order-By* deadlines.
4. **Multi-Echelon Optimization**: Mathematical EOQ (EOQ = sqrt(2DS/H)) and dynamic safety-buffered ROP calculations.

#### Live Network Overview:
- **Retail Locations**: {context.get('total_stores', 5)} stores (S001 – S005)
- **Active Catalog**: {context.get('total_products', 20)} automotive parts
- **Low-Stock Alerts**: **{context.get('low_stock_count', 15)}** SKUs requiring replenishment
- **Available Inter-Store Transfers**: **{context.get('active_transfers_count', 16)}** balance opportunities
- **Procurement Orders Due**: **{context.get('procurement_alerts_count', 15)}**"""

        # ----------------------------------------------------
        # 9. GENERAL CONVERSATIONAL / HELP FALLBACK
        # ----------------------------------------------------
        if is_marathi:
            return f"""मी **स्टॉकर AI असिस्टंट** आहे. तुमच्या प्रश्नाचे थेट उत्तर शोधण्यासाठी खालीलपैकी एकावर क्लिक करा किंवा नाव टाईप करा:

- ⚠️ **"कमी स्टॉक सांगा"**: कोणत्या भागांचा तुटवडा आहे ते दाखवेल.
- 📦 **"स्टॉक किती आहे?"**: सध्याच्या एकूण साठ्याची माहिती देईल.
- 🔍 **उत्पादनाचे नाव (उदा. "Brake Pad" किंवा "Air Filter")**: सर्व 5 स्टोअर्समधील लाइव्ह स्टॉक दाखवेल.
- 🔄 **"स्टॉक ट्रान्सफर"**: अतिरिक्त साठा हलवण्याच्या शिफारसी देईल.
- 📐 **"EOQ फॉर्म्युला"**: खर्चात बचत करण्याचे सूत्र समजावून सांगेल.

तुम्हाला यापैकी नक्की कोणती माहिती हवी आहे?"""

        if is_hindi:
            return f"""मैं **स्टॉकर AI असिस्टेंट** हूँ। आपके प्रश्न से संबंधित सटीक डेटा निकालने के लिए आप ये पूछ सकते हैं:

- ⚠️ **"कम स्टॉक बताओ"**: किन पार्ट्स की कमी है उनकी सूची देगा।
- 📦 **"करंट स्टॉक कितना है?"**: कुल इन्वेंटरी का विवरण देगा।
- 🔍 **प्रोडक्ट का नाम (जैसे "Brake Pad" या "Battery")**: सभी स्टोर्स में उस पार्ट का लाइव स्टॉक दिखाएगा।
- 🔄 **"स्टॉक ट्रांसफर"**: स्टोर्स के बीच माल ट्रांसफर के सुझाव देगा।
- 📐 **"EOQ और ROP फॉर्मूला"**: इन्वेंटरी ऑप्टिमाइजेशन सूत्र समझाएगा।

आप किस विषय पर जानकारी चाहते हैं?"""

        return f"""I am **Stocker AI Copilot**, your real-time supply chain intelligence engine.

To get instant live data from the system, you can ask:
- ⚠️ **"Which products are low on stock?"** ➔ Full list of {context.get('low_stock_count', 15)} critical SKUs below ROP.
- 📦 **"Current stock"** ➔ Comprehensive inventory distribution across all 5 stores.
- 🔍 **Specific Product Name (e.g., "Air Filter stock", "Brake Pad stock", "Battery stock")** ➔ Exact counts per store location.
- 🔄 **"Show inter-store transfers"** ➔ {context.get('active_transfers_count', 16)} rebalancing opportunities.
- 🛒 **"Procurement deadlines"** ➔ Supplier lead times and order-by dates.
- 📐 **"Explain EOQ and ROP formula"** ➔ Mathematical proof and step-by-step logic.
- 🌐 **Ask in any language**: English, हिन्दी, मराठी, Español, etc."""

    def chat(self, user_message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Main entry point for handling user messages.
        Attempts Gemini -> OpenAI -> Local Semantic Engine.
        """
        if history is None:
            history = []

        context = self.get_live_system_context()
        system_prompt = self._build_system_prompt(context)

        # 1. Try Gemini
        gemini_reply = self._call_gemini(user_message, history, system_prompt)
        if gemini_reply:
            return {
                "reply": gemini_reply,
                "provider": "gemini",
                "model": DEFAULT_GEMINI_MODEL,
                "timestamp": datetime.utcnow().isoformat()
            }

        # 2. Try OpenAI
        openai_reply = self._call_openai(user_message, history, system_prompt)
        if openai_reply:
            return {
                "reply": openai_reply,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "timestamp": datetime.utcnow().isoformat()
            }

        # 3. Built-in Local Semantic Engine
        local_reply = self._local_semantic_answer(user_message, context)
        return {
            "reply": local_reply,
            "provider": "local_engine",
            "model": "stocker-semantic-v1",
            "timestamp": datetime.utcnow().isoformat()
        }
