from collections import Counter

import click
from tqdm import tqdm
import requests
import csv
import time


def strip_prefixes(prefixes):
    ret = []
    for prefix in prefixes:
        prefix = prefix.replace('https://doi.org/', '')
        if prefix.endswith('/'):
            prefix = prefix[:-1]
        ret.append(prefix)
    return ret


@click.command
@click.argument("prefixes", nargs=-1)
@click.option("--output", default="datacite-check-output.csv")
def main(prefixes, output):
    prefixes = strip_prefixes(prefixes)
    f = open(output, "w")
    writer = csv.writer(f)

    writer.writerow(["doi", "title", "url", "registered", "status", "errors"])
    f.flush()

    # get count of records for tqdm
    total_count = 0
    for prefix in tqdm(prefixes, desc="Getting the number of DOIs"):
        data = requests.get(f"https://api.datacite.org/dois?prefix={prefix}&page[size]=1").json()
        for p in data["meta"]["prefixes"]:
            total_count += p['count']

    t = tqdm(total=total_count)
    stats = Counter()
    for prefix in prefixes:
        check_prefix(writer, f, stats, prefix, t)

    t.close()

    total = stats['ok'] + stats['error']
    if not total:
        total = 1

    okperc = int(100 * stats['ok'] / total)
    errperc = int(100 * stats['error'] / total)

    print("Overall stats: ")
    print(f"    ok records     : {stats['ok']} ({okperc} %)")
    print(f"    failed records : {stats['error']} ({errperc} %)")


def check_prefix(writer, csvfile, stats, prefix, t):
    page_url = f"https://api.datacite.org/dois?prefix={prefix}&page[size]=50"
    page = 0
    while page_url:
        time.sleep(1)
        page += 1
        t.set_description(f"Downloading metadata of {prefix}, page {page}")
        t.update(0)
        data = requests.get(page_url).json()
        page_url = data.get("links", {}).get("next")

        for rec in data["data"]:
            attrs = rec["attributes"]
            doi = attrs['doi']

            errors = check_record(t, attrs)
            titles = attrs.get("titles")
            if len(titles) > 0:
                title = titles[0].get("title")
            else:
                title = ""
            extra_attrs = [title, attrs.get("url", ''), attrs.get("registered")]

            if not errors:
                writer.writerow([doi, *extra_attrs, "ok"])
                stats['ok'] += 1
            else:
                writer.writerow([doi, *extra_attrs, "error", *errors])
                t.display(f"{doi}: " + ", ".join(errors))
                stats['error'] += 1
            csvfile.flush()

def check_record(t, attrs):
    doi = attrs['doi']
    url = attrs.get('url')
    registered = attrs.get("registered")
    t.set_description(f"Checking DOI {doi} -> {url}")
    t.update(1)

    errors = []
    if url:
        try:
            time.sleep(.5)
            resp = requests.get(url, allow_redirects=True)
            if resp.status_code != 200:
                errors.append(f"Landing page not reachable")
        except Exception as e:
            errors.append(f"Error getting landing page: {e}")
    else:
        errors.append("Landing page url not set")
    return errors


if __name__ == '__main__':
    main()