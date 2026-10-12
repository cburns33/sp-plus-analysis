"""Capture Week 7 displayed prices and grade the frozen cohort on a hosted runner."""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
GAMES = list(csv.DictReader((ROOT / 'week7_frozen.csv').open(encoding='utf-8')))
WINDOWS = {
    'thursday': ('2026-10-15', ['401860923']),
    'saturday-noon': ('2026-10-17', ['401862803']),
    'saturday-afternoon': ('2026-10-17', ['401856828', '401856719']),
    'saturday-early-evening': ('2026-10-17', ['401860903']),
    'saturday-evening': ('2026-10-17', ['401858263', '401862806', '401864520', '401858265', '401871091']),
    'saturday-late': ('2026-10-17', ['401866445', '401856833', '401864521']),
    'sunday-results': ('2026-10-18', [game['game_id'] for game in GAMES]),
}
DK_URL = ('https://dknetwork.draftkings.com/draftkings-sportsbook-betting-splits/'
          '?tb_eg=87637&itm_content=NCAA+Football&tb_edate=n30days&tb_emt=Spread&tb_page=')
SPORTSLINE = {
    '401862803': 'NCAAF_20261017_CHARLO%40TEMPLE',
    '401871091': 'NCAAF_20261017_LATECH%40LAMON',
    '401866445': 'NCAAF_20261017_OHIO%40SACST',
    '401864521': 'NCAAF_20261017_NMEX%40HAWAII',
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def norm(value):
    plain = ''.join(c for c in unicodedata.normalize('NFKD', value.lower())
                    if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', plain)


def match_score(game, title):
    if ' @ ' not in title:
        return 0
    away, home = title.split(' @ ', 1)
    return (SequenceMatcher(None, norm(game['away_team']), norm(away)).ratio() +
            SequenceMatcher(None, norm(game['home_team']), norm(home)).ratio()) / 2


def save_raw(window, name, response, dry_run):
    digest = hashlib.sha256(response.content).hexdigest()
    path = ROOT / 'raw' / f'{window}_{name}'
    if not dry_run:
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(response.content)
    return {'url': response.url, 'retrieved_at_utc': now(), 'sha256': digest,
            'snapshot': str(path.relative_to(ROOT))}


def dk_quotes(window, games, dry_run):
    found, sources = {}, []
    for page in range(1, 6):
        response = requests.get(DK_URL + str(page), timeout=30)
        response.raise_for_status()
        source = save_raw(window, f'dk_page{page}.html', response, dry_run)
        sources.append(source)
        soup = BeautifulSoup(response.content, 'html.parser')
        for heading in soup.select('h5'):
            title = heading.get_text(' ', strip=True)
            candidates = sorted(((match_score(game, title), game) for game in games),
                                key=lambda item: item[0], reverse=True)
            if not candidates or candidates[0][0] < 0.78 or (len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.1):
                continue
            game = candidates[0][1]
            event = heading.find_parent(class_='tb-se')
            if event is None:
                continue
            sides = []
            for row in event.select('.tb-sodd'):
                label, odds = row.select_one('.tb-slipline'), row.select_one('.tb-odd-s')
                if label is None or odds is None:
                    continue
                match = re.fullmatch(r'(.+) ([+-]\d+(?:\.\d+)?)', label.get_text(' ', strip=True))
                if match:
                    sides.append((match.group(1), float(match.group(2)),
                                  int(odds.get_text(' ', strip=True).replace('−', '-'))))
            dogs = [side for side in sides if side[1] > 0 and norm(side[0]) == norm(game['underdog'])]
            if len(dogs) == 1 and len(sides) == 2:
                found[game['game_id']] = {'underdog_points': dogs[0][1],
                                          'underdog_american': dogs[0][2],
                                          'source': 'DraftKings Network', 'source_game': title,
                                          **source}
    return found, sources


def sportsline_quote(window, game, dry_run):
    slug = SPORTSLINE.get(game['game_id'])
    if slug is None:
        return None, None
    url = f'https://www.sportsline.com/college-football/game-forecast/{slug}/'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    source = save_raw(window, f'sportsline_{game["game_id"]}.html', response, dry_run)
    soup = BeautifulSoup(response.content, 'html.parser')
    script = next((tag.string or tag.get_text() for tag in soup.find_all('script')
                   if 'oddsViews' in (tag.string or tag.get_text())), None)
    if script is None:
        return None, source
    script = script.replace('\\"', '"')
    start = script.find('"oddsViews":')
    if start < 0:
        return None, source
    views, _ = json.JSONDecoder().raw_decode(script[start + len('"oddsViews":'):])
    book = next((item for item in views['books'] if item['name'] == 'DraftKings'), None)
    if book is None:
        return None, source
    side = 'home' if game['underdog'] == game['home_team'] else 'away'
    quote = book['odds']['spread'][side]
    return {'underdog_points': float(quote['value']),
            'underdog_american': int(quote['odds']),
            'source': 'SportsLine embedded DraftKings',
            'source_game': f'{game["away_team"]} @ {game["home_team"]}', **source}, source


def capture(window, games, dry_run):
    quotes, sources = dk_quotes(window, games, dry_run)
    for game in games:
        if game['game_id'] not in quotes:
            quote, source = sportsline_quote(window, game, dry_run)
            if source:
                sources.append(source)
            if quote:
                quotes[game['game_id']] = quote
    records = []
    for game in games:
        quote = quotes.get(game['game_id'])
        seconds_before_kickoff = (datetime.fromisoformat(game['start_date_utc'].replace('Z', '+00:00')) -
                                  datetime.fromisoformat(quote['retrieved_at_utc'])).total_seconds() if quote else None
        records.append({'game_id': game['game_id'], 'underdog': game['underdog'],
                        'sp_selected': game['sp_selected'] == '1', 'quote': quote,
                        'captured_before_kickoff': bool(quote and seconds_before_kickoff >= 0),
                        'captured_near_kickoff': bool(quote and 0 <= seconds_before_kickoff <= 7200),
                        'missing_reason': None if quote else 'No matching displayed DraftKings spread and price'})
    return {'window': window, 'captured_at_utc': now(), 'records': records, 'sources': sources}


def grade(points, dog_score, favorite_score):
    margin = dog_score + points - favorite_score
    return 'W' if margin > 0 else 'L' if margin < 0 else 'P'


def return_for(grade_value, price):
    if grade_value == 'P':
        return 0.0
    if grade_value == 'L':
        return -100.0
    return 100 * (100 / abs(price) if price < 0 else price / 100)


def results(games, dry_run):
    prior = {}
    for path in sorted((ROOT / 'runs').glob('saturday-*.json')) + sorted((ROOT / 'runs').glob('thursday.json')):
        for record in json.loads(path.read_text(encoding='utf-8'))['records']:
            quote = record['quote']
            if record['captured_near_kickoff'] and quote:
                old = prior.get(record['game_id'])
                if old is None or quote['retrieved_at_utc'] > old['retrieved_at_utc']:
                    prior[record['game_id']] = quote
    records, sources = [], []
    for game in games:
        url = 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary'
        response = requests.get(url, params={'event': game['game_id']}, timeout=30)
        response.raise_for_status()
        source = save_raw('sunday-results', f'espn_{game["game_id"]}.json', response, dry_run)
        sources.append(source)
        competition = response.json()['header']['competitions'][0]
        complete = competition['status']['type']['completed']
        sides = {side['homeAway']: side for side in competition['competitors']}
        dog_side = 'home' if game['underdog'] == game['home_team'] else 'away'
        record = {'game_id': game['game_id'], 'underdog': game['underdog'],
                  'sp_selected': game['sp_selected'] == '1', 'final': complete,
                  'score_source': source, 'near_kickoff_quote': prior.get(game['game_id'])}
        if complete:
            dog_score = int(sides[dog_side]['score'])
            favorite_score = int(sides['away' if dog_side == 'home' else 'home']['score'])
            frozen_grade = grade(float(game['frozen_dk_underdog_points']), dog_score, favorite_score)
            record.update({'dog_score': dog_score, 'favorite_score': favorite_score,
                           'frozen_grade': frozen_grade,
                           'frozen_return_per_100': round(return_for(frozen_grade, int(game['initial_dk_underdog_american'])), 2)})
            quote = record['near_kickoff_quote']
            if quote:
                near_grade = grade(quote['underdog_points'], dog_score, favorite_score)
                record.update({'near_grade': near_grade,
                               'near_return_per_100': round(return_for(near_grade, quote['underdog_american']), 2)})
        records.append(record)
    summary = {}
    for label, group in [('all_large_dogs', records), ('sp_selected', [r for r in records if r['sp_selected']])]:
        summary[label] = {}
        for prefix in ('frozen', 'near'):
            graded = [r for r in group if prefix + '_grade' in r]
            summary[label][prefix] = {'games': len(graded),
                                      'wins': sum(r[prefix + '_grade'] == 'W' for r in graded),
                                      'losses': sum(r[prefix + '_grade'] == 'L' for r in graded),
                                      'pushes': sum(r[prefix + '_grade'] == 'P' for r in graded),
                                      'return_per_100_staked_each': round(sum(r[prefix + '_return_per_100'] for r in graded), 2)}
    return {'window': 'sunday-results', 'captured_at_utc': now(), 'records': records,
            'summary': summary, 'sources': sources}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--window', required=True, choices=WINDOWS)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--allow-early', action='store_true')
    args = parser.parse_args()
    expected_date, ids = WINDOWS[args.window]
    if not args.dry_run and not args.allow_early and datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d') != expected_date:
        print('Outside the one-time scheduled date; no capture')
        return
    games = [game for game in GAMES if game['game_id'] in ids]
    output = results(games, args.dry_run) if args.window == 'sunday-results' else capture(args.window, games, args.dry_run)
    metric = 'finals' if args.window == 'sunday-results' else 'quotes'
    count = sum(bool(r.get('final' if metric == 'finals' else 'quote')) for r in output['records'])
    print(args.window, 'games', len(output['records']), metric, count)
    if not args.dry_run:
        path = ROOT / 'runs' / f'{args.window}.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
