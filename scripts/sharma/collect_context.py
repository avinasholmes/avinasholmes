"""Collect free news metadata and bounded public social context, without scoring."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
from feeds import Store,collect_context,now,stamp

ROOT=Path(__file__).resolve().parents[2]


def merge_articles(previous,incoming,cutoff):
    end=stamp(cutoff);start=end-dt.timedelta(hours=24)
    merged={}
    for article in previous+incoming:
        try:
            seen=stamp(article['first_seen_at'])
            if not start<=seen<=end:continue
            identity=(article['ticker'],article['url'])
            old=merged.get(identity)
            if old is None or seen<stamp(old['first_seen_at']):merged[identity]=article
        except (KeyError,ValueError):continue
    return sorted(merged.values(),key=lambda a:stamp(a['first_seen_at']),reverse=True)[:5000]


def run(universe_path,symbols):
    universe=json.loads(Path(universe_path).read_text())['rows']
    allowed={r['ticker'] for r in universe}
    if not set(symbols)<=allowed:
        raise ValueError('Social symbols must be in the universe')
    target=ROOT/'sharma/data/context.json'
    try:previous=json.loads(target.read_text())
    except (FileNotFoundError,ValueError):previous={}
    store=Store(ROOT/'private-data/feeds.sqlite')
    statuses=collect_context(universe,store,symbols)
    current=now();recent=stamp(current)-dt.timedelta(hours=24)
    events=[e for e in store.available_events(current) if stamp(e['first_seen_at'])>=recent]
    articles=merge_articles(previous.get('news',[]),[e for e in events if e['kind']=='news'],current)
    successful=statuses['news']['status']=='connected'
    observed=current if successful else previous.get('news_observed_at',previous.get('observed_at',current))
    # Source article text and personal identifiers are not exported.
    public={'schema_version':1,'observed_at':observed,'news_observed_at':observed,
            'checked_at':current,'retained_after_error':not successful and bool(articles),'used_in_score':False,
            'attribution':{'label':'The GDELT Project','url':'https://www.gdeltproject.org/'},
            'statuses':statuses,'news':articles,'social_counts':{s:sum(e['kind']=='social' and e['ticker']==s for e in events) for s in symbols},
            'warnings':['Context collected after a historical price snapshot is not used in that earlier score.',
                        'GDELT tone is general article tone, not validated financial sentiment.',
                        'No news match does not establish absence of news.']}
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,mode='w',delete=False) as handle:
        json.dump(public,handle,indent=2,allow_nan=False);temporary=handle.name
    os.replace(temporary,target)
    print(json.dumps({'statuses':statuses,'article_stock_pairs':len(articles)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--universe',required=True)
    parser.add_argument('--social-symbols',default='AAPL,MSFT,NVDA,AMZN,GOOG,META,TSLA,AMD')
    args=parser.parse_args()
    run(args.universe,args.social_symbols.split(','))
