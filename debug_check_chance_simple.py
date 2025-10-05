import requests, re
base = 'http://127.0.0.1:5000'
nums = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
data = {f'numero{i+1}': str(n) for i, n in enumerate(nums)}
try:
    r = requests.post(base + '/predicao', data=data, timeout=5)
except Exception as e:
    print('request failed:', e)
    raise
print('status', r.status_code)
if r.status_code == 200:
    # accept id attributes with single or double quotes
    m = re.search(r"id=[\'\"]heatmap-badge[\'\"][\s\S]*?>([^<]+)<", r.text)
    if m:
        print('heatmap text->', m.group(1).strip())
    else:
        print('heatmap badge not found')
    m2 = re.search(r"id=[\'\"]soma-display[\'\"][^>]*>([^<]+)<", r.text)
    if m2:
        print('soma->', m2.group(1).strip())
    else:
        print('soma not found')
    m3 = re.search(r"id=[\'\"]predicao-block[\'\"][\s\S]*?</div>", r.text)
    if m3:
        snippet = m3.group(0)
        print('predicao-block snippet:\n', snippet[:400])
    else:
        print('predicao-block not found')
else:
    print('error body', r.text[:400])
