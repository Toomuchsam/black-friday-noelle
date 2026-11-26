import os, json, re, datetime, urllib.request, urllib.parse
from urllib.parse import urlsplit
RULES = {'cpu': {'4500U': 1, '4650U': 1, '1135G7': 1, '1145G7': 1, '1165G7': 1, '1185G7': 1, '5500U': 2, '5600U': 2, '5650U': 2, '5625U': 2, '5700U': 2, '5800U': 2, '5850U': 2, '5825U': 2, '7430U': 2, '7530U': 2, '7730U': 2, '1235U': 2, '1245U': 2, '1255U': 2, '1265U': 2, '1335U': 2, '1345U': 2, '1355U': 2, '1365U': 2, '6600U': 3, '6650U': 3, '6800U': 3, '6850U': 3, '7535U': 3, '7735U': 3, '7640U': 3, '7840U': 3, '8640U': 3, '8840U': 3, '125H': 3, '135H': 3, '155H': 3, '125U': 3, '135U': 3, '155U': 3, '225U': 3, '225H': 3, '235U': 3, '255H': 3}, 'brands': ['lenovo', 'thinkpad', 'thinkbook', 'ideapad', 'hp', 'elitebook', 'probook', 'pavilion', 'dell', 'latitude', 'inspiron', 'acer', 'aspire', 'swift', 'asus', 'vivobook', 'zenbook', 'msi', 'samsung', 'fujitsu', 'lifebook', 'dynabook', 'toshiba', 'huawei', 'honor', 'microsoft', 'surface'], 'sellers': ['back market', 'backmarket', 'afb', 'trade discount', 'trade-discount', 'laptopservice', 'laptop service', 'refurbed', 'rebuy', 'boulanger', 'darty', 'fnac', 'ldlc', 'materiel.net', 'lenovo', 'dell', 'hp', 'acer', 'asus', 'electro dépôt', 'pccomponentes', 'amazon', 'cdiscount', 'rakuten', 'carrefour', 'auchan', 'rue du commerce', 'easy cash', 'cash express', 'pc portable occasion', 'smaaart'], 'models': {'thinkpad t14 gen 1': 280, 'thinkpad t14 gen 2': 330, 'thinkpad t14 gen 3': 410, 'thinkpad x13 gen 2': 340, 'elitebook 840 g8': 300, 'elitebook 845 g8': 330, 'elitebook 830 g8': 290, 'latitude 5420': 280, 'latitude 5430': 350, 'latitude 5440': 400, 'latitude 5320': 270}}
from pathlib import Path

key = os.environ['SERPAPI_KEY']
now = datetime.datetime.now(datetime.timezone.utc)
path = Path('offres.json')
old = json.loads(path.read_text(encoding='utf-8'))
month = now.strftime('%Y-%m')
usage = old.get('usage', {})
count = usage.get('count', 0) if usage.get('month') == month else 0
if count >= 240:
    print('Limite mensuelle locale atteinte'); raise SystemExit(0)
queries = ['Lenovo ThinkPad T14 X13 Ryzen 5650U 16 Go SSD 512 Go reconditionné France', 'HP EliteBook 845 840 G8 G9 16 Go SSD 512 Go reconditionné France', 'Dell Latitude 5430 5440 5420 16 Go SSD 512 Go reconditionné France', 'PC portable Lenovo HP Acer Asus Ryzen 5 7430U 7530U 16 Go 512 Go neuf France', 'PC portable Lenovo HP Dell Acer Asus i5 1235U 1335U 16 Go 512 Go neuf France', 'site:backmarket.fr ordinateur portable ThinkPad EliteBook Latitude 16 Go 512 Go', 'site:trade-discount.com PC portable 16 Go 512 Go ThinkPad EliteBook Latitude', 'site:afbshop.fr PC portable 16 Go 512 Go ThinkPad EliteBook Latitude', 'PC portable ThinkPad EliteBook Latitude Ryzen 5 i5 16 Go SSD 1 To reconditionné', 'PC portable 13 14 pouces Ryzen 5 5650U i5 1235U 16 Go 512 Go reconditionné']
q = queries[count % len(queries)]
old['usage'] = {'month': month, 'count': count+1}
path.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding='utf-8')
engine = 'google' if count % 2 else 'google_shopping'
print('Moteur:', engine, 'Requête:', q)
params = dict(engine=engine, q=q, google_domain='google.fr', gl='fr', hl='fr', api_key=key)
try:
    with urllib.request.urlopen('https://serpapi.com/search.json?'+urllib.parse.urlencode(params), timeout=45) as r:
        data = json.load(r)
except Exception:
    print('Requête API échouée, anciennes offres conservées'); raise SystemExit(1)
if data.get('error'):
    print('Erreur API, anciennes offres conservées'); raise SystemExit(1)
by_id = {(o['name'],o.get('seller','')):o for o in old['offers']}
items = data.get('shopping_results', []) if engine == 'google_shopping' else data.get('organic_results', [])
print('Résultats bruts:', len(items))
rejections = {}
def reject(reason):
    rejections[reason] = rejections.get(reason, 0) + 1
    print('Rejet:', reason, '|', title[:180])
for item in items:
    title = item.get('title','')
    text = title + ' ' + str(item.get('snippet',''))
    price = item.get('extracted_price')
    if engine == 'google' and price is None:
        prices = re.findall(r'(?<!\d)(\d{2,3}(?:[,.]\d{2})?)\s*€', text)
        if len(set(prices)) == 1: price = float(prices[0].replace(',', '.'))
    url = item.get('link') or item.get('product_link')
    if item.get('price') and '€' not in str(item['price']):
        reject("item.get('price') and '€' not in str(item['price'])"); continue
    if not isinstance(price,(int,float)) or not 0 < price < 450 or not url or not url.startswith('https://'):
        reject('Prix ou lien non admissible'); continue
    if not re.search(r'\b(?:16|24|32|48|64)\s*(?:go|gb)\b',text,re.I):
        reject('RAM non confirmée'); continue
    if re.search(r'\b(?:4|8)\s*(?:go|gb)\s*(?:de\s+)?(?:ram|ddr[345])',text,re.I):
        reject("re.search(r'\\b(?:4|8)\\s*(?:go|gb)\\s*(?:de\\s+)?(?:ram|ddr[345])',text,re.I)"); continue
    if not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb)|1024\s*(?:go|gb))\b',text,re.I):
        reject("not re.search(r'\\b(?:512\\s*(?:go|gb)|[12]\\s*(?:to|tb)|1024\\s*(?:go|gb))\\b',text,re.I)"); continue
    if not re.search(r'ryzen\s*[579]|(?:core\s*)?i[579]\b|core\s*(?:ultra\s*)?[579]\b',text,re.I):
        reject("not re.search(r'ryzen\\s*[579]|(?:core\\s*)?i[579]\\b|core\\s*(?:ultra\\s*)?[579]\\b',text,re.I)"); continue
    size = re.search(r'\b(1[3456](?:[.,][0-9])?)\s*(?:pouces|inch|["″])',text,re.I)
    seller = item.get('source') or urlsplit(url).hostname or 'Vendeur à confirmer'
    domains = {'backmarket.fr':'Back Market','trade-discount.com':'Trade Discount','afbshop.fr':'AfB','laptopservice.fr':'LaptopService','refurbed.fr':'Refurbed'}
    host = urlsplit(url).hostname or ''
    for domain, label in domains.items():
        if host == domain or host.endswith('.'+domain): seller = label
    if not any(re.search(r'\b'+re.escape(x)+r'\b', title, re.I) for x in RULES['brands']):
        reject("not any(re.search(r'\\b'+re.escape(x)+r'\\b', title, re.I) for x in RULES['brands'])"); continue
    if not any(x in seller.lower() for x in RULES['sellers']):
        reject("not any(x in seller.lower() for x in RULES['sellers'])"); continue
    codes = set(re.findall(r'\b(?:i[3579][ -]?)?(\d{4}(?:G[147]|[UHY]|HS|HX)|\d{3}[UH])\b',text.upper()))
    if codes and (len(codes)!=1 or not codes.issubset(RULES['cpu'])):
        reject('CPU hors sélection ou ambigu'); continue
    if size and float(size.group(1).replace(',','.')) >= 16:
        reject("size and float(size.group(1).replace(',','.')) >= 16"); continue
    identity = (title,seller)
    previous = by_id.get(identity,{})
    history = previous.get('history',[])
    if not history or history[-1]['price'] != price or history[-1]['date'][:10] != now.date().isoformat():
        history.append({'date':now.isoformat(timespec='minutes'),'price':price})
    condition = 'Reconditionné' if re.search(r'reconditionn|refurbished|renewed',text,re.I) else ('Neuf' if re.search(r'\bneuf\b|\bnew\b',text,re.I) else 'À confirmer')
    if re.search(r'\b(?:pour pièces|hors service|sans chargeur|écran cassé)\b',text,re.I):
        reject("re.search(r'\\b(?:pour pièces|hors service|sans chargeur|écran cassé)\\b',text,re.I)"); continue
    if re.search(r'\b(?:i[579]-[2-7]\d{3}|ryzen\s*[579]\s*[12]\d{3})\b',text,re.I):
        reject("re.search(r'\\b(?:i[579]-[2-7]\\d{3}|ryzen\\s*[579]\\s*[12]\\d{3})\\b',text,re.I)"); continue
    by_id[identity] = dict(name=title,seller=seller,price=price,size=float(size.group(1).replace(',','.')) if size else 0,condition=condition,specs=text,verified=False,note='Piste Google Shopping : vérifier prix livré, état, CPU exact, RAM, SSD, Windows 11, IPS, AZERTY et USB. Taille 0 = inconnue.',url=url,history=history[-50:],seen=now.isoformat(),first_seen=previous.get("first_seen") or (history[0]["date"] if history else now.isoformat()),image=item.get("thumbnail") or previous.get("image", ""))
cutoff = now-datetime.timedelta(days=3)
old['offers'] = list(by_id.values())
old['updated'] = now.isoformat(timespec='minutes')
path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
print('Rejets détaillés:', json.dumps(rejections, ensure_ascii=False))
print('Pistes enregistrées :',len(old['offers']))
