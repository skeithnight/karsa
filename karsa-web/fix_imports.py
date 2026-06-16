import glob

hook_files = glob.glob('src/hooks/*/index.ts')
for hook_file in hook_files:
    with open(hook_file, 'r') as f:
        content = f.read()
    
    if 'import { ApiError }' not in content:
        content = 'import { ApiError } from "../../api/errors/api-error";\n' + content
        
    with open(hook_file, 'w') as f:
        f.write(content)

print("Imports fixed")
