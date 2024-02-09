#!/usr/bin/env python3 -u

"""
  This uses the Brave search API:
  https://api.search.brave.com/app/documentation/web-search/get-started

  The API requires you sign up and obtain an API key (see BRAVE_API_KEY, below).

  Example of using the API via a Curl client:
  curl -s --compressed "https://api.search.brave.com/res/v1/web/search?q=$query" \
    -H "Accept: application/json" \
    -H "Accept-Encoding: gzip" \
    -H "X-Subscription-Token: $( cat ./Brave_Search_API_Key.txt )"

"""

T_SLEEP_MS = 100 # Avoid rate limiting from Brave search API
MAX_RETRIES = 3
N_COLS = 8

import re, sys, os, time, json, random
import urllib.parse
import fileinput
import datetime
import html
import requests

addr_pat = re.compile(r"^addr:(?:city|postcode|street)=(.+)$")
rate_pat = re.compile(r'"ratingValue": +(\d\.\d)')

api_key = os.getenv("BRAVE_API_KEY")
if api_key is None:
  print("Environment variable BRAVE_API_KEY must be set. Quitting.")
  sys.exit(1)

# Save all the JSON data here for future use (it costs a bit of $).
out = open("brave_api.ndjson", 'a')

def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)

# Given an array of query terms, return the FLOAT value of its rating (1 - 5).
def get_rating(query_terms):
  q = ' '.join(query_terms)
  rv = None
  q = urllib.parse.quote_plus(q)
  hdrs = {
    "Accept": "application/json"
    , "Accept-Encoding": "gzip"
    , "X-Subscription-Token": api_key
  }
  url = "https://api.search.brave.com/res/v1/web/search?q={}".format(q)
  # See: https://requests.readthedocs.io/en/latest/user/advanced/,
  # https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
  r = None
  for x in range(0, MAX_RETRIES):
    try:
      r = requests.get(url, headers=hdrs, timeout=(0.93, 2.71))
      break
    except requests.exceptions.Timeout:
      pass
    except requests.exceptions.ConnectionError:
      time.sleep(random.randint(50, 2000)/1000)
  if r is None:
    eprint("URL: {} returned None".format(url))
    return rv
  obj = r.json()
  out.write(json.dumps(obj) + '\n')
  """
  The "ratingValue" field occurs at various places:
    $.web.results.0.location.rating.ratingValue
    $.web.results.9.review.rating.ratingValue
    rv = obj["web"]["results"][0]["location"]["rating"]["ratingValue"]
    ... so just go with a regular expression:
  """
  mat = rate_pat.search(json.dumps(obj))
  if mat is not None:
    rv = mat.group(1)
  return rv

for line in fileinput.input():
  line = line.rstrip()
  a = line.split('<')
  if N_COLS != len(a):
    continue
  (id, dt, uid, lat, lon, name, kvagg, geohash) = a
  terms = [name]
  # Only need name and kvagg
  for x in kvagg.split('|'):
    if len(x) == 0:
      continue;
    x = html.unescape(x)
    x = re.sub(r"['\",{}]", "", x)
    m = addr_pat.match(x)
    if m is not None:
      terms.append(m.group(1))
  rating = get_rating(terms)
  if rating is not None:
    a.append(rating)
    a.append(datetime.datetime.now().isoformat())
  else:
    a.append("")
    a.append("")
  print('<'.join(a))
  time.sleep(T_SLEEP_MS/1000)

out.close()

