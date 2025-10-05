import requests
from html import unescape

base = 'http://127.0.0.1:5000'

def fetch_and_extract(source):
    try:
        url = base + f'/admin/dashboard?source={source}'
        r = requests.get(url, timeout=10)
        print('\n---', source, 'status', r.status_code)
        text = r.text
        start_marker = 'Pares / Ímpares (por jogo)'
        end_marker = 'Top Faixas de Soma'
        start = text.find(start_marker)
        end = text.find(end_marker, start if start!=-1 else 0)
        if start == -1 or end == -1:
            print('could not find expected markers for', source)
            # fallback: print a chunk around start_marker
            ix = text.find(start_marker)
            if ix == -1:
                print('start marker not found at all')
                return
            snippet = text[ix:ix+1200]
        else:
            snippet = text[start:end]
        # find the first <ul after the marker (pairs) and the next <ul> (odds)
        ul_pos = snippet.find('<ul')
        if ul_pos == -1:
            print('no ul found for', source)
            return
        remaining = snippet[ul_pos:]
        lists = []
        pos = 0
        while len(lists) < 2:
            i = remaining.find('<ul', pos)
            if i == -1:
                break
            j = remaining.find('</ul>', i)
            if j == -1:
                break
            ul_html = remaining[i:j]
            # extract li text
            import re
            items = []
            p = 0
            while True:
                li_start = ul_html.find('<li', p)
                if li_start == -1:
                    break
                li_end = ul_html.find('</li>', li_start)
                if li_end == -1:
                    break
                li = ul_html[li_start:li_end]
                textli = re.sub('<[^>]+>', '', li).strip()
                textli = unescape(textli)
                if textli:
                    items.append(textli)
                p = li_end + 5
            lists.append(items)
            pos = j + 5
        print('pairs items:', len(lists[0]) if lists else 0)
        if lists:
            for it in lists[0][:10]:
                print('-', it)
        print('odds items:', len(lists[1]) if len(lists) > 1 else 0)
        if len(lists) > 1:
            for it in lists[1][:10]:
                print('-', it)
    except Exception as e:
        print('error', e)

if __name__ == '__main__':
    fetch_and_extract('predicoes')
    fetch_and_extract('concursos')
    
