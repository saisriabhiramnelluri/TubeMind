import os
import re
import sys

# Define a more comprehensive emoji pattern or simply rely on character ranges
# This covers most standard emojis
emoji_pattern = re.compile(r'[\U0001f300-\U0001f64f\U0001f680-\U0001f6ff\U00002600-\U000026ff\U00002700-\U000027bf\U0001f900-\U0001f9ff\U0001fa70-\U0001faff]', flags=re.UNICODE)

cwd = os.getcwd()

for root, dirs, files in os.walk(cwd):
    if 'venv' in dirs: dirs.remove('venv')
    if '.git' in dirs: dirs.remove('.git')
    if '__pycache__' in dirs: dirs.remove('__pycache__')
    
    for file in files:
        if file.endswith(('.py', '.js', '.html', '.css', '.md', '.txt', '.yaml', '.json')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if emoji_pattern.search(line):
                        print(f"{filepath}:{i+1}: {line.strip()}")
            except Exception as e:
                pass
