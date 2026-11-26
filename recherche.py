import os, json, re, datetime, urllib.request, urllib.parse
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
queries = [
    'PC portable neuf Ryzen 5 Ryzen 7 16 Go SSD 512 Go Windows 11 moins de 450 euros',
    'Lenovo ThinkPad T14 X13 L14 reconditionné 16 Go SSD 512 Go AZERTY',
    'PC portable neuf Intel Core i5 i7 Core Ultra 5 16 Go SSD 512 Go Windows 11',
    'HP EliteBook 830 840 845 ProBook 440 445 reconditionné 16 Go SSD 512 Go',
    'Dell Latitude 5320 5420 5430 5440 reconditionné 16 Go SSD 512 Go',
    'PC portable Ryzen 5 Core i5 16 Go SSD 1 To moins de 450 euros',
    'PC portable 13 14 pouces Ryzen 5 Core i5 16 Go SSD 512 Go AZERTY',
    'Black Friday PC portable Ryzen 5 Core i5 16 Go SSD 512 Go promotion France',
]
q = queries[count % len(queries)]
old['usage'] = {'month': month, 'count': count+1}
path.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding='utf-8')
params = dict(engine='google_shopping', q=q, google_domain='google.fr', gl='fr', hl='fr', api_key=key)
try:
    with urllib.request.urlopen('https://serpapi.com/search.json?'+urllib.parse.urlencode(params), timeout=45) as r:
        data = json.load(r)
except Exception:
    print('Requête API échouée, anciennes offres conservées'); raise SystemExit(0)
if data.get('error') or 'shopping_results' not in data:
    print('Résultats indisponibles, anciennes offres conservées'); raise SystemExit(0)
by_id = {(o['name'],o.get('seller','')):o for o in old['offers']}
for item in data['shopping_results']:
    title = item.get('title','')
    text = title + ' ' + str(item.get('snippet',''))
    price = item.get('extracted_price')
    url = item.get('link') or item.get('product_link')
    if item.get('price') and '€' not in str(item['price']): continue
    if not isinstance(price,(int,float)) or not 0 < price < 450 or not url or not url.startswith('https://'): continue
    if not re.search(r'\b(?:16|24|32|48|64)\s*(?:go|gb)\b',text,re.I): continue
    if re.search(r'\b(?:4|8)\s*(?:go|gb)\s*(?:de\s+)?(?:ram|ddr[345])',text,re.I): continue
    if not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb)|1024\s*(?:go|gb))\b',text,re.I): continue
    if not re.search(r'ryzen\s*[579]|(?:core\s*)?i[579]\b|core\s*(?:ultra\s*)?[579]\b',text,re.I): continue
    size = re.search(r'\b(1[3456](?:[.,][0-9])?)\s*(?:pouces|inch|["″])',text,re.I)
    seller = item.get('source','Vendeur à confirmer')
    identity = (title,seller)
    previous = by_id.get(identity,{})
    history = previous.get('history',[])
    if not history or history[-1]['price'] != price:
        history.append({'date':now.isoformat(timespec='minutes'),'price':price})
    condition = 'Reconditionné' if re.search(r'reconditionn|refurbished|renewed',text,re.I) else ('Neuf' if re.search(r'\bneuf\b|\bnew\b',text,re.I) else 'À confirmer')
    if re.search(r'\b(?:pour pièces|hors service|sans chargeur|écran cassé)\b',text,re.I): continue
    if re.search(r'\b(?:i[579]-[2-7]\d{3}|ryzen\s*[579]\s*[12]\d{3})\b',text,re.I): continue
    by_id[identity] = dict(name=title,seller=seller,price=price,size=float(size.group(1).replace(',','.')) if size else 0,condition=condition,specs=text,verified=False,note='Piste Google Shopping : vérifier prix livré, état, CPU exact, RAM, SSD, Windows 11, IPS, AZERTY et USB. Taille 0 = inconnue.',url=url,history=history[-50:],seen=now.isoformat(),first_seen=previous.get("first_seen") or (history[0]["date"] if history else now.isoformat()),image=item.get("thumbnail") or previous.get("image", ""))
cutoff = now-datetime.timedelta(days=3)
old['offers'] = list(by_id.values())
old['updated'] = now.isoformat(timespec='minutes')
path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
print('Pistes enregistrées :',len(old['offers']))
