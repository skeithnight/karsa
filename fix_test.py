with open('tests/karsa/thesis/test_repositories_batch3_remediation.py', 'r') as f:
    lines = f.readlines()

out = []
for line in lines:
    if line.strip() == "pass":
        continue
    out.append(line)

with open('tests/karsa/thesis/test_repositories_batch3_remediation.py', 'w') as f:
    f.writelines(out)
