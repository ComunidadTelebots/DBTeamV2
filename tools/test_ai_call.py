import urllib.request, json, os

def call_ai(prompt):
    url='http://127.0.0.1:8081/ai/gpt2'
    payload=json.dumps({'prompt':prompt,'max_length':60}).encode('utf-8')
    req=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as r:
        return r.read().decode('utf-8')

def save_scene(name, text):
    base=os.path.join(os.path.dirname(__file__), '..', 'data', 'streams', 'scenes')
    os.makedirs(base, exist_ok=True)
    path=os.path.join(base, name + '.json')
    obj={'name': name, 'ai_generated': [{'text': text}]}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path

if __name__=='__main__':
    prompt='Write a short caption for a live stream about cute cats.'
    try:
        out=call_ai(prompt)
        print('AI response:', out)
        p=save_scene('ai-test-scene', out)
        print('Saved scene to', p)
    except Exception as e:
        print('Error:', e)
