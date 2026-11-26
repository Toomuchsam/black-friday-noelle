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
    'PC portable Ryzen 5 16 Go SSD 512 Go Windows 11 neuf',
    'PC portable Core i5 16 Go SSD 512 Go Windows 11 neuf',
    'PC portable Ryzen 5 16 Go SSD 512 Go reconditionné',
    'PC portable Core i5 16 Go SSD 512 Go reconditionné',
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
    if not isinstance(price,(int,float)) or not 0 < price < 450 or not url or not url.startswith('https://'): continue
    if not re.search(r'\b(?:16|24|32|64)\s*(?:go|gb)\b',text,re.I): continue
    if not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb)|1024\s*(?:go|gb))\b',text,re.I): continue
    if not re.search(r'ryzen\s*[579]|(?:core\s*)?i[579]\b|core\s*(?:ultra\s*)?[579]\b',text,re.I): continue
    size = re.search(r'\b(1[3456](?:[.,][0-9])?)\s*(?:pouces|inch|["″])',text,re.I)
    seller = item.get('source','Vendeur à confirmer')
    identity = (title,seller)
    previous = by_id.get(identity,{})
    history = previous.get('history',[])
    if not history or history[-1]['price'] != price:
        history.append({'date':now.isoformat(timespec='minutes'),'price':price})
    condition = 'Reconditionné' if re.search(r'reconditionn|refurbished|renewed',text,re.I) else 'À confirmer'
    by_id[identity] = dict(name=title,seller=seller,price=price,size=float(size.group(1).replace(',','.')) if size else 0,condition=condition,specs=text,verified=False,note='Piste Google Shopping : vérifier prix livré, état, CPU exact, RAM, SSD, Windows 11, IPS, AZERTY et USB. Taille 0 = inconnue.',url=url,history=history[-50:],seen=now.isoformat())
cutoff = now-datetime.timedelta(days=3)
old['offers'] = [o for o in by_id.values() if o.get('verified') or (o.get('seen') and datetime.datetime.fromisoformat(o['seen'])>=cutoff)]
old['updated'] = now.isoformat(timespec='minutes')
path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
print('Pistes enregistrées :',len(old['offers']))
