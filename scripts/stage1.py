# Stage 1: IDs + dates for each (country, class). Direct P31 classes, no subclass traversal (fast).
import requests, time, json, os
EP="https://query.wikidata.org/sparql"
H={"User-Agent":"MaRoimDataset/0.1 (nadav167@gmail.com)","Accept":"application/sparql-results+json"}
FILM=["Q11424","Q506240","Q202866","Q1261214","Q93204","Q120243801","Q98807719","Q98701476",
      "Q122914801","Q20650540","Q12912091","Q104840802","Q123126551"]
TV=["Q5398426","Q15416","Q1259759","Q526877","Q117467246","Q117467240","Q581714","Q63952888",
    "Q1273568","Q170238","Q16889492","Q133731271","Q137613441","Q113480583","Q62573441","Q73505270",
    "Q4765080","Q9335576","Q775344","Q98526239","Q116515088","Q113671041","Q17145545"]
QF="""SELECT ?item (MIN(YEAR(?d)) AS ?start) WHERE { ?item wdt:P31 wd:%s ; wdt:P495 wd:%s ; wdt:P577 ?d .
 FILTER(?d >= "1980-01-01"^^xsd:dateTime) } GROUP BY ?item"""
QT="""SELECT ?item (MIN(YEAR(?s)) AS ?start) (MIN(YEAR(?p)) AS ?pub) (MAX(YEAR(?e)) AS ?end) WHERE {
 ?item wdt:P31 wd:%s ; wdt:P495 wd:%s .
 OPTIONAL{?item wdt:P580 ?s} OPTIONAL{?item wdt:P577 ?p} OPTIONAL{?item wdt:P582 ?e} } GROUP BY ?item"""
OUT="raw/stage1"; os.makedirs(OUT,exist_ok=True)
for cc,cq in [("IL","Q801"),("US","Q30")]:
  for kind,classes,Q in [("film",FILM,QF),("tv",TV,QT)]:
    for cls in classes:
      f=f"{OUT}/{cc}_{kind}_{cls}.json"
      if os.path.exists(f): continue
      for a in range(5):
        try:
          r=requests.post(EP,data={"query":Q%(cls,cq)},headers=H,timeout=120)
          if r.status_code==429: time.sleep(30); continue
          r.raise_for_status()
          rows=[{k:v["value"] for k,v in b.items()} for b in r.json()["results"]["bindings"]]
          json.dump(rows,open(f,"w")); print(cc,kind,cls,len(rows),flush=True); break
        except Exception as e: print("retry",cc,cls,e,flush=True); time.sleep(15*(a+1))
      else: print("FAILED",cc,kind,cls,flush=True)
print("DONE")
