import os, json, re, datetime, urllib.request, urllib.parse
from urllib.parse import urlsplit
RULES = {'cpu': {'4500U': 1, '4650U': 1, '1135G7': 1, '1145G7': 1, '1165G7': 1, '1185G7': 1, '5500U': 2, '5600U': 2, '5650U': 2, '5625U': 2, '5700U': 2, '5800U': 2, '5850U': 2, '5825U': 2, '7430U': 2, '7530U': 2, '7730U': 2, '1235U': 2, '1245U': 2, '1255U': 2, '1265U': 2, '1335U': 2, '1345U': 2, '1355U': 2, '1365U': 2, '6600U': 3, '6650U': 3, '6800U': 3, '6850U': 3, '7535U': 3, '7735U': 3, '7640U': 3, '7840U': 3, '8640U': 3, '8840U': 3, '125H': 3, '135H': 3, '155H': 3, '125U': 3, '135U': 3, '155U': 3, '225U': 3, '225H': 3, '235U': 3, '255H': 3}, 'brands': ['lenovo', 'thinkpad', 'thinkbook', 'ideapad', 'hp', 'elitebook', 'probook', 'pavilion', 'dell', 'latitude', 'inspiron', 'acer', 'aspire', 'swift', 'asus', 'vivobook', 'zenbook', 'msi', 'samsung', 'fujitsu', 'lifebook', 'dynabook', 'toshiba', 'huawei', 'honor', 'microsoft', 'surface'], 'sellers': ['back market', 'backmarket', 'afb', 'trade discount', 'trade-discount', 'laptopservice', 'laptop service', 'refurbed', 'rebuy', 'boulanger', 'darty', 'fnac', 'ldlc', 'materiel.net', 'lenovo', 'dell', 'hp', 'acer', 'asus', 'electro dépôt', 'pccomponentes', 'amazon', 'cdiscount', 'rakuten', 'carrefour', 'auchan', 'rue du commerce', 'easy cash', 'cash express', 'pc portable occasion', 'smaaart'], 'models': {'thinkpad t14 gen 1': 280, 'thinkpad t14 gen 2': 330, 'thinkpad t14 gen 3': 410, 'thinkpad x13 gen 2': 340, 'elitebook 840 g8': 300, 'elitebook 845 g8': 330, 'elitebook 830 g8': 290, 'latitude 5420': 280, 'latitude 5430': 350, 'latitude 5440': 400, 'latitude 5320': 270}}
from pathlib import Path


def classify(o):
    t=o['name']+' '+o.get('specs','')
    bad=[]; missing=[]
    price=o.get('price',0)
    if price>400: bad.append('Hors budget')
    if not price:
        missing.append('Prix inconnu')
        prices=re.findall(r'(?<!\d)(\d{2,4})\s*€\s*(\d{2})?',t)
        if prices and all(float(a)+float(b or 0)/100>400 for a,b in prices):
            bad.append('Prix mentionnés supérieurs au budget')
    if not any(re.search(r'\b'+re.escape(x)+r'\b',o['name'],re.I) for x in RULES['brands']): bad.append('Marque non retenue')
    if not any(x in o.get('seller','').lower() for x in RULES['sellers']): bad.append('Vendeur non retenu')
    codes=set(re.findall(r'\b(?:I[3579][ -]?)?(\d{4,5}(?:G[147]|HS|HX|[UHY])|\d{3}[UH])\b',t.upper()))
    if codes and not codes.issubset(RULES['cpu']): bad.append('CPU non retenu')
    if len(codes)!=1: missing.append('CPU exact')
    sizes=[float(x.replace(',','.')) for x in re.findall(r'\b(1[0-9](?:[.,]\d+)?)\s*(?:pouces?|inches?|["″])',t,re.I)]
    if o.get('size'): sizes.append(o['size'])
    if any(x<13 or x>=15 for x in sizes): bad.append('Écran hors critères')
    if not sizes: missing.append('Taille écran')
    if re.search(r'\b(?:4|8)\s*(?:go|gb)\s*(?:de\s+)?(?:ram|ddr)',t,re.I): bad.append('RAM insuffisante')
    if not re.search(r'\b(?:16|24|32|48|64)\s*(?:go|gb)\b',t,re.I): missing.append('RAM 16 Go')
    if not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb)|1024\s*(?:go|gb))\b',t,re.I): missing.append('SSD 512 Go')
    if re.search(r'pour pièces|hors service|écran cassé|sans chargeur',t,re.I): bad.append('État incompatible')
    for pattern,label in [(r'windows\s*11','Windows 11'),(r'\bips\b','IPS'),(r'azerty','AZERTY'),(r'\busb\b','USB')]:
        if not re.search(pattern,t,re.I): missing.append(label)
    return ('archive' if bad else 'piste' if not price else 'prometteuse' if missing else 'conforme'),bad+missing

def main():
    key=os.environ['SERPAPI_KEY']
    now=datetime.datetime.now(datetime.timezone.utc)
    path=Path('offres.json')
    old=json.loads(path.read_text(encoding='utf-8'))
    month=now.strftime('%Y-%m')
    usage=old.get('usage',{})
    count=usage.get('count',0) if usage.get('month')==month else 0
    limit=int(os.getenv('SERPAPI_MONTHLY_LIMIT','240'))
    queries=['ThinkPad T14 X13 Ryzen 5650U 16 Go 512 Go reconditionné','EliteBook 845 840 G8 G9 16 Go 512 Go reconditionné','Latitude 5420 5430 5440 16 Go 512 Go reconditionné','PC portable 14 pouces Ryzen 5 7430U 7530U 16 Go 512 Go neuf','PC portable 13 14 pouces i5 1235U 1335U 16 Go 512 Go neuf','site:backmarket.fr ThinkPad EliteBook Latitude 16 Go 512 Go','site:trade-discount.com PC portable 16 Go 512 Go','site:afbshop.fr PC portable 16 Go 512 Go']
    by_id={(o['name'],o.get('seller','')):o for o in old.get('offers',[])}
    logs=[]; errors=0; success=0
    for _ in range(2):
        if count>=limit: break
        engine='google_shopping' if count%2==0 else 'google'
        q=queries[(count//2)%len(queries)]
        count+=1
        print(engine,q)
        params=dict(engine=engine,q=q,google_domain='google.fr',gl='fr',hl='fr',api_key=key)
        try:
            with urllib.request.urlopen('https://serpapi.com/search.json?'+urllib.parse.urlencode(params),timeout=45) as response:
                data=json.load(response)
            field='shopping_results' if engine=='google_shopping' else 'organic_results'
            if data.get('error') or field not in data: raise ValueError('Réponse API indisponible')
        except Exception as exc:
            errors+=1
            logs.append({'engine':engine,'query':q,'error':type(exc).__name__})
            print('Erreur API',type(exc).__name__)
            continue
        success+=1
        for item in data[field]:
            title=item.get('title','')
            url=item.get('link') or item.get('product_link') or ''
            if not title or not url.startswith('https://'): continue
            t=title+' '+str(item.get('snippet',''))
            price=item.get('extracted_price',0)
            if not isinstance(price,(int,float)) or price<0: price=0
            if item.get('price') and '€' not in str(item['price']): price=0
            seller=item.get('source') or urlsplit(url).hostname or ''
            size=re.search(r'\b(1[0-9](?:[.,]\d+)?)\s*(?:pouces?|inches?|["″])',t,re.I)
            identity=(title,seller)
            previous=by_id.get(identity,{})
            history=list(previous.get('history',[]))
            if price and (not history or history[-1]['price']!=price or history[-1]['date'][:10]!=now.date().isoformat()):
                history.append({'date':now.isoformat(timespec='minutes'),'price':price})
            o=dict(name=title,seller=seller,price=price,size=float(size.group(1).replace(',','.')) if size else 0,condition='Reconditionné' if re.search(r'reconditionn|refurbished',t,re.I) else 'Neuf' if re.search(r'\bneuf\b',t,re.I) else 'À confirmer',specs=t,verified=False,url=url,history=history[-50:],seen=now.isoformat(),first_seen=previous.get('first_seen',now.isoformat()),image=item.get('thumbnail') or previous.get('image',''),origin=engine,note='Prix livré, stock, garantie et état à vérifier chez le vendeur.')
            category,reasons=classify(o)
            o.update(category=category,reasons=reasons)
            logs.append({'name':title,'category':category,'reasons':reasons})
            print(category,title,'; '.join(reasons))
            if category!='archive' or identity in by_id: by_id[identity]=o
    for o in by_id.values():
        category,reasons=classify(o)
        try:
            if now-datetime.datetime.fromisoformat(o['seen'])>datetime.timedelta(days=3):
                category='archive'; reasons.append('Relevé ancien')
        except (KeyError,ValueError,TypeError):
            category='archive'; reasons.append('Date inconnue')
        o.update(category=category,reasons=reasons)
    old.update(offers=list(by_id.values()),usage={'month':month,'count':count},last_attempt=now.isoformat(),diagnostics=logs,status='partiel' if errors and success else 'erreur' if errors else 'ok' if success else 'quota')
    if success: old['updated']=now.isoformat(timespec='minutes')
    path.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Requêtes réussies',success,'erreurs',errors,'compteur local',count)
    return int(bool(errors))

if __name__=='__main__':
    raise SystemExit(main())
