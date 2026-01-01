import os
here = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(here, '..'))
env_path = os.path.join(repo_root, '.env')
print('here=', here)
print('repo_root=', repo_root)
print('env_path=', env_path)
print('exists=', os.path.exists(env_path))
if os.path.exists(env_path):
    with open(env_path,'r',encoding='utf-8') as f:
        for i,l in enumerate(f):
            if i>10: break
            print(repr(l))
