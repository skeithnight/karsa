import os

files = [
    'src/app/page.tsx',
    'src/app/portfolio/page.tsx',
    'src/app/research/page.tsx',
    'src/app/theses/page.tsx',
    'src/app/theses/[id]/page.tsx',
    'src/app/memos/page.tsx',
    'src/app/analysts/page.tsx',
    'src/app/performance/page.tsx',
    'src/app/oversight/page.tsx',
    'src/app/infrastructure/page.tsx',
]

for file in files:
    if os.path.exists(file):
        with open(file, 'r') as f:
            print(f"--- {file} ---")
            print(f.read())
            print(f"--- END {file} ---\n")
    else:
        print(f"File {file} does not exist.")

