import glob
import re

page_files = glob.glob('src/app/**/page.tsx', recursive=True)

for file in page_files:
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove import { AppLayout }
    content = re.sub(r"import\s*\{\s*AppLayout\s*\}\s*from\s*'[^']+';\n", "", content)
    
    # Replace <AppLayout> and </AppLayout> with <></>
    content = content.replace("<AppLayout>", "<>")
    content = content.replace("</AppLayout>", "</>")
    
    with open(file, 'w') as f:
        f.write(content)

print("Pages fixed")
