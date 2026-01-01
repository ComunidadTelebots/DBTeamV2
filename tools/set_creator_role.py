import sys
sys.path.insert(0, 'projects/bot')
from python_bot.storage import storage

uid = 163103382
storage.set_role(uid, 'creator')
print('set_role->', storage.get_role(uid))
