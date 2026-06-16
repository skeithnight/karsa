import glob
import re

files = glob.glob('src/features/*/types/viewmodels.ts')
for f in files:
    print(f"--- {f} ---")
    with open(f, 'r') as file:
        print(file.read())
