import glob

d = 'backend/app/services/providers'
for f in glob.glob(d + '/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if "'{prompt}'" in content:
        content = content.replace("'{prompt}'", "the requested topic")
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print('Fixed', f)
