import requests
from bs4 import BeautifulSoup

base='http://127.0.0.1:5000'
# choose a valid 15-number game
nums=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
# prepare data
data={f'numero{i+1}':str(n) for i,n in enumerate(nums)}
resp = requests.post(base+'/predicao', data=data)
print('status', resp.status_code)
if resp.status_code==200:
    soup = BeautifulSoup(resp.text, 'html.parser')
    badge = soup.find(id='heatmap-badge')
    soma = soup.find(id='soma-display')
    print('soma element:', soma.text if soma else None)
    print('heatmap badge raw:', badge.text if badge else None)
    # print predicao block
    pred = soup.find(id='predicao-block')
    if pred:
        print('predicao block present')
        print(pred.get_text()[:400])
    else:
        print('no predicao block')
else:
    print(resp.text[:400])
