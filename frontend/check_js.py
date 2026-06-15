import urllib.request
import re
req = urllib.request.Request('https://grayn-aeo.vercel.app/')
html = urllib.request.urlopen(req).read().decode()
chunks = re.findall(r'src=\"(/_next/static/chunks/app/page-[^\"]+\.js)\"', html)
if chunks:
    js_url = 'https://grayn-aeo.vercel.app' + chunks[0]
    js = urllib.request.urlopen(js_url).read().decode()
    if '"/v1/report"' in js:
        # get around context
        idx = js.find('"/v1/report"')
        print(js[max(0, idx-100):min(len(js), idx+100)])
    else:
        for chunk in chunks[1:]:
            js_url = 'https://grayn-aeo.vercel.app' + chunk
            js = urllib.request.urlopen(js_url).read().decode()
            idx = js.find('"/v1/report"')
            if idx != -1:
                print(js[max(0, idx-100):min(len(js), idx+100)])
