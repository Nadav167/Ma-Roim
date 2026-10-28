# Stage 2: details for each collected item, batched with VALUES
import requests, time, json, os, glob, collections
from concurrent.futures import ThreadPoolExecutor
EP="https://query.wikidata.org/sparql"
H={"User-Agent":"MaRoimDataset/0.1 (nadav167@gmail.com)","Accept":"application/sparql-results+json"}
# merge stage1: item -> {kinds, countries, year}
items={}
def yi(r,k): return int(r[k]) if k in r else None
for f in glob.glob("raw/stage1/*.json"):
    c,k,cls=os.path.basename(f)[:-5].split("_")
    for r in json.load(open(f)):
        qid=r["item"].rsplit("/",1)[1]
        ys=[y for y in (yi(r,"start"),yi(r,"pub")) if y]
        d=items.setdefault(qid,{"kinds":set(),"cq":set(),"year":None,"end":None})
        d["kinds"].add(k); d["cq"].add(c)
        if ys: d["year"]=min(ys+([d["year"]] if d["year"] else []))
        if yi(r,"end"): d["end"]=max(yi(r,"end"),d["end"] or 0)
print("items",len(items),flush=True)
Q="""SELECT ?item (SAMPLE(?en) AS ?en) (SAMPLE(?he) AS ?he) (SAMPLE(?imdb) AS ?imdb) (SAMPLE(?mc) AS ?mc)
 (SAMPLE(?enwiki) AS ?enwiki) (SAMPLE(?hewiki) AS ?hewiki) (MAX(YEAR(?end)) AS ?endyear)
 (GROUP_CONCAT(DISTINCT ?gl; separator="|") AS ?genres)
 (GROUP_CONCAT(DISTINCT ?cl; separator="|") AS ?countries)
 (GROUP_CONCAT(DISTINCT ?tl; separator="|") AS ?types) WHERE {
 VALUES ?item { %s }
 OPTIONAL { ?item rdfs:label ?en FILTER(LANG(?en)="en") }
 OPTIONAL { ?item rdfs:label ?he FILTER(LANG(?he)="he") }
 OPTIONAL { ?item wdt:P345 ?imdb }
 OPTIONAL { ?item wdt:P1712 ?mc }
 OPTIONAL { ?item wdt:P582 ?end }
 OPTIONAL { ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }
 OPTIONAL { ?hewiki schema:about ?item ; schema:isPartOf <https://he.wikipedia.org/> }
 OPTIONAL { ?item wdt:P136 ?g . ?g rdfs:label ?gl FILTER(LANG(?gl)="en") }
 OPTIONAL { ?item wdt:P495 ?c . ?c rdfs:label ?cl FILTER(LANG(?cl)="en") }
 OPTIONAL { ?item wdt:P31 ?t . ?t rdfs:label ?tl FILTER(LANG(?tl)="en") }
} GROUP BY ?item"""
OUT="raw/stage2"; os.makedirs(OUT,exist_ok=True)
ids=sorted(items); B=150
batches=[ids[i:i+B] for i in range(0,len(ids),B)]
def run(i):
    f=f"{OUT}/{i:05d}.json"
    if os.path.exists(f): return
    vals=" ".join("wd:"+q for q in batches[i])
    for a in range(6):
        try:
            r=requests.post(EP,data={"query":Q%vals},headers=H,timeout=120)
            if r.status_code==429: time.sleep(int(r.headers.get("Retry-After",30))); continue
            r.raise_for_status()
            out=[{k:v["value"] for k,v in b.items()} for b in r.json()["results"]["bindings"]]
            json.dump(out,open(f,"w")); 
            if i%50==0: print("batch",i,"/",len(batches),flush=True)
            return
        except Exception as e:
            print("retry",i,e,flush=True); time.sleep(10*(a+1))
    print("FAILED",i,flush=True)
with ThreadPoolExecutor(3) as ex: list(ex.map(run,range(len(batches))))
json.dump({q:{"kinds":sorted(d["kinds"]),"cq":sorted(d["cq"]),"year":d["year"],"end":d["end"]} for q,d in items.items()},open("raw/items.json","w"))
print("DONE")
