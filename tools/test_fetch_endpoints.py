import urllib.request
urls=['http://127.0.0.1:8000/multimedia.html','http://127.0.0.1:8082/media/stream/doesnotexist.mp4']
for u in urls:
    try:
        r=urllib.request.urlopen(u,timeout=5)
        print(u, r.getcode())
    except Exception as e:
        print(u, 'ERR', e)
