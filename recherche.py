import os, json, re, datetime, urllib.request, urllib.parse
from urllib.parse import urlsplit
RULES = {'cpu': {'4500U': 1, '4650U': 1, '1135G7': 1, '1145G7': 1, '1165G7': 1, '1185G7': 1, '5500U': 2, '5600U': 2, '5650U': 2, '5625U': 2, '5700U': 2, '5800U': 2, '5850U': 2, '5825U': 2, '7430U': 2, '7530U': 2, '7730U': 2, '1235U': 2, '1245U': 2, '1255U': 2, '1265U': 2, '1335U': 2, '1345U': 2, '1355U': 2, '1365U': 2, '6600U': 3, '6650U': 3, '6800U': 3, '6850U': 3, '7535U': 3, '7735U': 3, '7640U': 3, '7840U': 3, '8640U': 3, '8840U': 3, '125H': 3, '135H': 3, '155H': 3, '125U': 3, '135U': 3, '155U': 3, '225U': 3, '225H': 3, '235U': 3, '255H': 3}, 'brands': ['lenovo', 'thinkpad', 'thinkbook', 'ideapad', 'hp', 'elitebook', 'probook', 'pavilion', 'dell', 'latitude', 'inspiron', 'acer', 'aspire', 'swift', 'asus', 'vivobook', 'zenbook', 'msi', 'samsung', 'fujitsu', 'lifebook', 'dynabook', 'toshiba', 'huawei', 'honor', 'microsoft', 'surface'], 'sellers': ['back market', 'backmarket', 'afb', 'trade discount', 'trade-discount', 'laptopservice', 'laptop service', 'refurbed', 'rebuy', 'boulanger', 'darty', 'fnac', 'ldlc', 'materiel.net', 'lenovo', 'dell', 'hp', 'acer', 'asus', 'electro dépôt', 'pccomponentes', 'amazon', 'cdiscount', 'rakuten', 'carrefour', 'auchan', 'rue du commerce', 'easy cash', 'cash express', 'pc portable occasion', 'smaaart'], 'models': {'thinkpad t14 gen 1': 280, 'thinkpad t14 gen 2': 330, 'thinkpad t14 gen 3': 410, 'thinkpad x13 gen 2': 340, 'elitebook 840 g8': 300, 'elitebook 845 g8': 330, 'elitebook 830 g8': 290, 'latitude 5420': 280, 'latitude 5430': 350, 'latitude 5440': 400, 'latitude 5320': 270}}
from pathlib import Path


def classify(o):
    t=o['name']+' '+o.get('specs','')
    bad=[]; missing=[]
    if o.get('manual_rejection'): bad.append(o['manual_rejection'])
    if re.search(r'\b(?:qwerty|qwertz)\b|clavier\s+(?:anglais|allemand|espagnol|italien)',t,re.I): bad.append('Clavier non AZERTY')
    price=o.get('price',0)
    if price>400: bad.append('Hors budget')
    if not price:
        missing.append('Prix inconnu')
        prices=re.findall(r'(?<!\d)(\d{2,4})\s*€\s*(\d{2})?',t)
        if prices and all(float(a)+float(b or 0)/100>400 for a,b in prices):
            bad.append('Prix mentionnés supérieurs au budget')
    if not any(re.search(r'\b'+re.escape(x)+r'\b',o['name'],re.I) for x in RULES['brands']): bad.append('Marque non retenue')
    if not any(x in o.get('seller','').lower() for x in RULES['sellers']): missing.append('Fiabilité vendeur à vérifier')
    codes=set(re.findall(r'\b(?:I[3579][ -]?)?(\d{4,5}(?:G[147]|HS|HX|[UHY])|\d{3}[UH])\b',t.upper()))
    if codes and not codes.intersection(RULES['cpu']): missing.append('Performances CPU à confirmer')
    if len(codes)!=1: missing.append('CPU exact')
    sizes=[float(x.replace(',','.')) for x in re.findall(r'\b(1[0-9](?:[.,]\d+)?)\s*(?:pouces?|inches?|["″])',t,re.I)]
    if o.get('size'): sizes.append(o['size'])
    if sizes and all(x<13 or x>=15 for x in sizes): bad.append('Écran hors critères')
    elif any(x<13 or x>=15 for x in sizes): missing.append('Taille écran ambiguë')
    if not sizes: missing.append('Taille écran')
    if re.search(r'\b(?:4|8)\s*(?:go|gb)\s*(?:de\s+)?(?:ram|ddr)',t,re.I): bad.append('RAM insuffisante')
    if not re.search(r'\b(?:16|24|32|48|64)\s*(?:go|gb)\b',t,re.I): missing.append('RAM 16 Go')
    if re.search(r'\b(?:128|256)\s*(?:go|gb)\s*(?:ssd|nvme)|\b(?:ssd|nvme)\s*(?:de\s+)?(?:128|256)\s*(?:go|gb)',t,re.I) and not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb))',t,re.I): bad.append('SSD insuffisant')
    if not re.search(r'\b(?:512\s*(?:go|gb)|[12]\s*(?:to|tb)|1024\s*(?:go|gb))\b',t,re.I): missing.append('SSD 512 Go')
    if re.search(r'pour pièces|hors service|écran cassé|sans chargeur|batterie hs|état correct|état moyen',t,re.I): bad.append('État incompatible')
    if not re.search(r'comme neuf|excellent état|état parfait|\bneuf\b',t,re.I): missing.append('État exact à vérifier')
    if re.search(r'rupture de stock|épuisé|indisponible',t,re.I): bad.append('Stock indisponible')
    missing.append('Livraison et stock à confirmer')
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
    queries=["Lenovo ThinkPad T14 Gen 2 Ryzen 5650U 16 Go 512 Go reconditionné 400 euros","HP EliteBook 845 G8 Ryzen 5650U 16 Go 512 Go reconditionné","Dell Latitude 5420 5430 i5 16 Go 512 Go reconditionné 400 euros","HP EliteBook 840 G8 16 Go 512 Go AZERTY","Lenovo ThinkPad X13 Gen 2 16 Go 512 Go reconditionné","HP EliteBook 830 G8 16 Go 512 Go","Dell Latitude 5320 5330 16 Go 512 Go","Lenovo IdeaPad Slim 3 14 Ryzen 5 16 Go 512 Go promotion","Acer Aspire 14 Asus Vivobook 14 Ryzen 5 16 Go 512 Go promotion","site:backmarket.fr ThinkPad EliteBook Latitude 16 Go 512 Go","site:trade-discount.com 14 pouces 16 Go 512 Go","site:afbshop.fr 14 pouces 16 Go 512 Go","site:smaaart.fr EliteBook ThinkPad 16 Go 512 Go","site:refurbed.fr ThinkPad EliteBook 16 Go 512 Go","site:laptopservice.fr Latitude EliteBook 16 Go 512 Go","site:boulanger.com PC portable 14 Ryzen 5 16 Go 512 Go"]
    queries += ["PC portable 14 pouces 16 Go 512 Go AZERTY Windows 11 moins de 400 euros", "ThinkPad L14 T14s Gen 2 16 Go 512 Go AZERTY", "HP ProBook 440 G8 G9 16 Go 512 Go AZERTY", "Dell Latitude 5430 7330 7430 16 Go 512 Go AZERTY", "site:pcportableoccasion.com 16 Go 512 Go 14 pouces", "site:fnac.com ordinateur portable 14 16 Go 512 Go", "site:darty.com ordinateur portable 14 16 Go 512 Go", "site:cdiscount.com ordinateur portable 14 16 Go 512 Go AZERTY"]
    by_id={(o['name'],o.get('seller','')):o for o in old.get('offers',[])}
    rejected_urls={o.get('url') for o in old.get('offers',[]) if o.get('manual_rejection') and o.get('url')}
    logs=[]; errors=0; success=0
    daily_budget=2
    # Six cycles par jour, plafond mensuel conservé.
    for _ in range(min(daily_budget, max(0, limit-count))):
        if count>=limit: break
        engine='google_shopping' if count%3==0 else 'google'
        q=queries[count%len(queries)]
        count+=1
        print(engine,q)
        params=dict(engine=engine,q=q,google_domain='google.fr',gl='fr',hl='fr',api_key=key)
        if engine=='google': params['num']=30
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
            t=title+' '+str(item.get('snippet',''))+' '+str(item.get('rich_snippet',{}))+' '+str(item.get('extensions',[]))
            price=item.get('extracted_price',0)
            if not isinstance(price,(int,float)) or price<0: price=0
            if item.get('price') and '€' not in str(item['price']): price=0
            if engine=='google' and not price:
                matches=re.findall(r'(?<![\d.,])(\d{2,4})(?:[,.](\d{2}))?\s*€(?:\s*(\d{2})(?!\d))?',t)
                values={int(a)+int(b or c or '0')/100 for a,b,c in matches}
                if len(values)==1 and not re.search(r'à partir de|dès |par mois|mensualité',t,re.I):
                    price=values.pop()
            if engine=='google' and re.search(r'/categorie/|/categories/|/search[/?]|/recherche[/?]',url,re.I): continue
            seller=item.get('source') or urlsplit(url).hostname or ''
            if not any(x in seller.lower() for x in RULES['sellers']):
                seller=next((x for x in RULES['sellers'] if x.replace(' ','').replace('-','') in (urlsplit(url).hostname or '').replace('-','')),seller)
            size=re.search(r'\b(1[0-9](?:[.,]\d+)?)\s*(?:pouces?|inches?|["″])',t,re.I)
            identity=(title,seller)
            previous=by_id.get(identity,{})
            history=list(previous.get('history',[]))
            if price and (not history or history[-1]['price']!=price or history[-1]['date'][:10]!=now.date().isoformat()):
                history.append({'date':now.isoformat(timespec='minutes'),'price':price})
            o=dict(name=title,seller=seller,price=price,size=float(size.group(1).replace(',','.')) if size else 0,condition='Reconditionné' if re.search(r'reconditionn|refurbished',t,re.I) else 'Neuf' if re.search(r'\bneuf\b',t,re.I) else 'À confirmer',specs=t,verified=False,url=url,history=history[-50:],seen=now.isoformat(),first_seen=previous.get('first_seen',now.isoformat()),image=item.get('thumbnail') or previous.get('image',''),origin=engine,note='Prix livré, stock, garantie et état à vérifier chez le vendeur.')
            if previous.get('manual_rejection') or url in rejected_urls: o['manual_rejection']=previous.get('manual_rejection') or 'Annonce déjà écartée manuellement'
            category,reasons=classify(o)
            o.update(category=category,reasons=reasons)
            logs.append({'name':title,'category':category,'reasons':reasons})
            print(category,title,'; '.join(reasons))
            by_id[identity]=o
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
