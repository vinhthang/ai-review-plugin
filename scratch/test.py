import os
try:
    with open('scripts/peer_review.py', 'r') as f:
        lines = f.readlines()
        print(''.join(lines[444:495]))
except Exception as e:
    print(e)
