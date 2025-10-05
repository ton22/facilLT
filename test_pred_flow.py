import requests, sys
base='http://127.0.0.1:5000'
s=requests.Session()
try:
    r=s.get(base+'/sugestao_automatica',timeout=5)
    print('sugestao status',r.status_code)
    print('json', r.json())
    sug = r.json().get('numeros')
except Exception as e:
    print('sug error',e); sys.exit(1)
if not sug:
    print('no suggestion returned'); sys.exit(1)
# prepare form data for /predicao
data = {f'numero{i+1}': str(num) for i,num in enumerate(sug)}
try:
    r2 = s.post(base+'/predicao', data=data, timeout=15)
    print('predicao status', r2.status_code)
    if r2.status_code==200:
        text = r2.text
        print('first 3 sug numbers present?', all(str(n) in text for n in sug[:3]))
        found = ('Pontuação' in text) or ('pontuação' in text) or ('Pontuacao' in text) or ('pontuacao' in text) or ('pontuação estimada' in text)
        print('pontuacao visible?', found)
        # print small snippet
        snippet = text[:1000]
        print('response snippet:\n', snippet)
    else:
        print('post failed status', r2.status_code)
        print(r2.text[:1000])
except Exception as e:
    print('post error', e)
