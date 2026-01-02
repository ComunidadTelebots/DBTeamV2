import json, urllib.request
u='http://127.0.0.1:8082/media/files'
print('GET',u)
try:
    r=urllib.request.urlopen(u,timeout=5)
    data=json.loads(r.read().decode())
    files=data.get('files',[])
    print('total files:', len(files))
    # show first 50
    for f in files[:50]:
        path=f.get('path')
        print('-', path)
    # show mp4s and bases
    mp4s=[f for f in files if f.get('path','').lower().endswith('.mp4')]
    print('\nmp4 count:', len(mp4s))
    for m in mp4s:
        base=m['path'].rsplit('.',1)[0]
        print('MP4:', m['path'], 'base=', base)
    # compute bases map
    bases={}
    for f in files:
        base=f['path'].rsplit('.',1)[0]
        bases.setdefault(base,[]).append(f['path'])
    # show bases that have both torrent and mp4
    print('\nBases with both .torrent and .mp4:')
    for b,items in bases.items():
        has_t = any(it.lower().endswith('.torrent') for it in items)
        has_m = any(it.lower().endswith('.mp4') for it in items)
        if has_t and has_m:
            print(' -', b, '->', items)
except Exception as e:
    print('ERR',e)
