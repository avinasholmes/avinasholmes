"""Server-side feed adapters. No trading endpoints or secrets in output."""
import datetime as dt
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).isoformat()


def stamp(value):
    result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(UTC)


def request(url, headers=None, limit=50_000_000):
    req = urllib.request.Request(url, headers={'User-Agent':'SharmaIndicatorResearch/0.2', **(headers or {})})
    # No immediate retry of 429/403 and no attempt to evade access controls.
    with urllib.request.urlopen(req, timeout=40) as response:
        data = response.read(limit+1)
        if len(data)>limit:
            raise ValueError('Feed response exceeds configured limit')
        return data


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS bars(feed TEXT,symbol TEXT,t TEXT,open REAL,high REAL,low REAL,close REAL,volume REAL,observed_at TEXT,PRIMARY KEY(feed,symbol,t));
          CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT,symbol TEXT,event_at TEXT,first_seen_at TEXT,payload TEXT);
          CREATE TABLE IF NOT EXISTS predictions(id TEXT PRIMARY KEY,issued_at TEXT,as_of TEXT,forecast_end TEXT,mode TEXT,payload TEXT);
        ''')

    def event(self, kind, symbol, event_at, payload, identity, observed_at=None):
        identifier=hashlib.sha256(f'{kind}:{symbol}:{identity}'.encode()).hexdigest()
        first_seen=observed_at or now()
        stamp(event_at);stamp(first_seen)
        self.db.execute('INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?)',
                        (identifier,kind,symbol,event_at,first_seen,json.dumps(payload,allow_nan=False)))
        self.db.commit()

    def available_events(self, cutoff, kind=None):
        # Availability uses our first observation, never publication time alone.
        end=stamp(cutoff)
        rows=self.db.execute('SELECT kind,symbol,event_at,first_seen_at,payload FROM events').fetchall()
        return [{'kind':k,'ticker':s,'event_at':t,'first_seen_at':seen,**json.loads(p)}
                for k,s,t,seen,p in rows if stamp(seen)<=end and stamp(t)<=end and (kind is None or k==kind)]

    def prediction(self, snapshot, issued_at=None):
        issued=issued_at or now()
        cut=stamp(snapshot['as_of'])
        # Even a timely calculation is not proof it was served to a visitor.
        for row in snapshot['rows']:
            if row['score'] is None:
                continue
            end=stamp(row['forecast_end'])
            mode='prospective_candidate' if cut<=stamp(issued)<min(end,cut+dt.timedelta(seconds=120)) else 'replay'
            body=json.dumps({'model':snapshot['model'],**row},sort_keys=True,allow_nan=False)
            ident=hashlib.sha256(body.encode()).hexdigest()
            self.db.execute('INSERT OR IGNORE INTO predictions VALUES(?,?,?,?,?,?)',
                            (ident,issued,snapshot['as_of'],row['forecast_end'],mode,body))
        self.db.commit()


class Alpaca:
    """Explicit feed selection; no silent SIP/IEX substitution or mixed bars."""
    def __init__(self, feed='iex'):
        if feed not in ('iex','sip'):
            raise ValueError('Select iex or sip explicitly')
        self.feed=feed
        key,secret=os.environ.get('APCA_API_KEY_ID'),os.environ.get('APCA_API_SECRET_KEY')
        if not key or not secret:
            raise ValueError('Alpaca credentials not configured; set server-side environment variables')
        self.headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret}

    def clock(self):
        base=os.environ.get('APCA_API_BASE_URL','https://paper-api.alpaca.markets').rstrip('/')
        if base not in ('https://paper-api.alpaca.markets','https://api.alpaca.markets'):
            raise ValueError('Unexpected Alpaca clock host')
        return json.loads(request(base+'/v2/clock',self.headers))

    def bars(self,symbols,start,end,store):
        if len(set(symbols))!=len(symbols):
            raise ValueError('Duplicate symbols')
        query={'symbols':','.join(symbols),'timeframe':'1Min','start':stamp(start).isoformat(),
               'end':stamp(end).isoformat(),'feed':self.feed,'limit':10000,'adjustment':'raw','sort':'asc'}
        count=0;seen_tokens=set();pages=0
        while True:
            url='https://data.alpaca.markets/v2/stocks/bars?'+urllib.parse.urlencode(query)
            data=json.loads(request(url,self.headers));observed=now();pages+=1
            # A symbol-sorted response may contain only the first securities.
            # Paginate all pages, including pages with no bars for some symbols.
            for symbol,bars in data.get('bars',{}).items():
                if symbol not in symbols:
                    raise ValueError('Unexpected response symbol')
                for b in bars:
                    t=stamp(b['t'])
                    if t+dt.timedelta(minutes=1)>stamp(end):
                        continue
                    values=[b[k] for k in ['o','h','l','c','v']]
                    if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in values) or min(values[:4])<=0 or values[4]<0:
                        continue
                    store.db.execute('INSERT OR REPLACE INTO bars VALUES(?,?,?,?,?,?,?,?,?)',
                                     (self.feed,symbol,t.isoformat(),*values,observed));count+=1
            store.db.commit()
            token=data.get('next_page_token')
            if not token:
                break
            if token in seen_tokens or pages>=500:
                raise ValueError('Pagination did not terminate')
            seen_tokens.add(token);query['page_token']=token
            time.sleep(.35) # stays below 200 HTTP requests/minute
        return {'status':'connected','provider':'Alpaca','feed':self.feed,'bars':count,'pages':pages,'observed_at':now()}


def normalize(value):
    value=re.sub(r'\([^)]*\)',' ',value.lower())
    value=re.sub(r'\b(incorporated|inc|corporation|corp|plc|ltd|limited|the|class|a|b)\b',' ',value)
    return ' '.join(re.findall(r'[a-z0-9]+',value))


def alias_map(universe):
    aliases={}
    for row in universe:
        name=normalize(row['name'])
        if len(name)>=5:
            aliases.setdefault(name,set()).add(row['ticker'])
    # Explicit identity aliases; never infer a company from an ordinary word ticker.
    for alias,symbol in {'apple':'AAPL','microsoft':'MSFT','nvidia':'NVDA','alphabet':'GOOGL',
                         'google':'GOOG','amazon':'AMZN','meta platforms':'META','tesla':'TSLA',
                         'advanced micro devices':'AMD','jpmorgan chase':'JPM'}.items():
        if any(r['ticker']==symbol for r in universe):
            aliases.setdefault(alias,set()).add(symbol)
    return aliases


def parse_gkg(text,universe,store,observed_at=None):
    aliases=alias_map(universe);matched=set();records=0
    for line in text.splitlines():
        fields=line.split('\t')
        if len(fields)<16:
            continue
        url=fields[4]
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname:
            continue
        organizations={normalize(v) for v in fields[13].split(';') if v}
        symbols=set().union(*(aliases.get(org,set()) for org in organizations)) if organizations else set()
        if not symbols:
            continue
        event_at=dt.datetime.strptime(fields[1],'%Y%m%d%H%M%S').replace(tzinfo=UTC).isoformat()
        try:
            tone=float(fields[15].split(',')[0])
            if not math.isfinite(tone):tone=None
        except ValueError:
            tone=None
        for symbol in symbols:
            store.event('news',symbol,event_at,{'url':url,'publisher':parsed.hostname,
                        'tone':tone,'source':'GDELT GKG','match':'organization entity; unverified',
                        'used_in_score':False},url,observed_at)
            matched.add(symbol);records+=1
    return {'matched_symbols':len(matched),'matched_article_stock_pairs':records}


def gdelt(universe,store):
    listing=request('https://data.gdeltproject.org/gdeltv2/lastupdate.txt',limit=10000).decode()
    candidate=next(line.split() for line in listing.splitlines() if line.endswith('.gkg.csv.zip'))
    url=candidate[2].replace('http://','https://',1)
    if not re.fullmatch(r'https://data\.gdeltproject\.org/gdeltv2/\d{14}\.gkg\.csv\.zip',url):
        raise ValueError('Unexpected GDELT archive location')
    raw=request(url)
    if hashlib.md5(raw).hexdigest()!=candidate[1]:
        raise ValueError('GDELT archive checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        files=archive.infolist()
        if len(files)!=1 or files[0].file_size>250_000_000:
            raise ValueError('Unexpected GDELT archive structure')
        text=archive.read(files[0]).decode('utf-8',errors='replace')
    observed=now()
    return {'status':'connected','provider':'GDELT GKG','observed_at':observed,
            'batch':url.rsplit('/',1)[-1][:14],'scope':'latest 15-minute batch; entity matching is incomplete',
            **parse_gkg(text,universe,store,observed)}


def bluesky(symbols,store):
    checked=[];count=0
    for symbol in symbols:
        # Cashtags constrain ambiguous tickers but still contain unverified claims.
        url='https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?'+urllib.parse.urlencode({'q':'$'+symbol,'sort':'latest','limit':25})
        payload=json.loads(request(url));checked.append(symbol);observed=now()
        for post in payload.get('posts',[]):
            record=post.get('record',{});created=record.get('createdAt');uri=post.get('uri')
            if not created or not uri:
                continue
            # Do not expose post text, identities or financial claims as facts.
            store.event('social',symbol,created,{'source':'Bluesky','used_in_score':False},uri,observed);count+=1
        time.sleep(1)
    return {'status':'connected','provider':'Bluesky','observed_at':now(),
            'checked_symbols':checked,'posts':count,'scope':'bounded cashtag search; not all social activity'}


def collect_context(universe,store,social_symbols):
    statuses={}
    for kind,run in [('news',lambda:gdelt(universe,store)),('social',lambda:bluesky(social_symbols,store))]:
        try:
            statuses[kind]=run()
        except urllib.error.HTTPError as exc:
            statuses[kind]={'status':'unavailable','http_status':exc.code,'observed_at':now(),
                            'reason':'Access refused or rate limited; no sentiment inferred'}
        except Exception as exc:
            statuses[kind]={'status':'unavailable','observed_at':now(),'reason':type(exc).__name__}
    return statuses
