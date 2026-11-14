"""Collect free news metadata and bounded public social context, without scoring."""
import argparse
import datetime as dt
import json
from pathlib import Path
from feeds import Store,collect_context,now,stamp

ROOT=Path(__file__).resolve().parents[2]


def run(universe_path,symbols):
    universe=json.loads(Path(universe_path).read_text())['rows']
    allowed={r['ticker'] for r in universe}
    if not set(symbols)<=allowed:
        raise ValueError('Social symbols must be in the universe')
    store=Store(ROOT/'private-data/feeds.sqlite')
    statuses=collect_context(universe,store,symbols)
    current=now();recent=stamp(current)-dt.timedelta(hours=24)
    events=[e for e in store.available_events(current) if stamp(e['first_seen_at'])>=recent]
    articles=[e for e in events if e['kind']=='news']
    # Source article text and personal identifiers are not exported.
    public={'schema_version':1,'observed_at':current,'used_in_score':False,
            'attribution':{'label':'The GDELT Project','url':'https://www.gdeltproject.org/'},
            'statuses':statuses,'news':articles,'social_counts':{s:sum(e['kind']=='social' and e['ticker']==s for e in events) for s in symbols},
            'warnings':['Context collected after a historical price snapshot is not used in that earlier score.',
                        'GDELT tone is general article tone, not validated financial sentiment.',
                        'No news match does not establish absence of news.']}
    (ROOT/'sharma/data/context.json').write_text(json.dumps(public,indent=2,allow_nan=False))
    print(json.dumps({'statuses':statuses,'article_stock_pairs':len(articles)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--universe',required=True)
    parser.add_argument('--social-symbols',default='AAPL,MSFT,NVDA,AMZN,GOOG,META,TSLA,AMD')
    args=parser.parse_args()
    run(args.universe,args.social_symbols.split(','))
