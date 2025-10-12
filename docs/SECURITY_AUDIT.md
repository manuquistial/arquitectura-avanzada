# 🔒 Security Audit - Comprehensive Security Testing

**Security Scanning & Vulnerability Assessment**

**Fecha**: 2025-10-13  
**Versión**: 1.0  
**Autor**: Manuel Jurado

---

## 📋 Índice

1. [Introducción](#introducción)
2. [Security Tools](#security-tools)
3. [Container Scanning (Trivy)](#container-scanning-trivy)
4. [Dependency Audit](#dependency-audit)
5. [Secrets Scanning](#secrets-scanning)
6. [SAST (Static Analysis)](#sast-static-analysis)
7. [DAST (Dynamic Analysis)](#dast-dynamic-analysis)
8. [Security Workflow](#security-workflow)
9. [Running Scans](#running-scans)
10. [Security Report](#security-report)
11. [Best Practices](#best-practices)

---

## 🎯 Introducción

El **Security Audit** realiza escaneos comprehensivos para detectar:

- 🐳 **Container vulnerabilities**: CVEs en imágenes Docker
- 📦 **Dependency vulnerabilities**: NPM, Python packages
- 🔑 **Secrets exposure**: API keys, passwords en código
- 🛡️ **Code vulnerabilities**: SQL injection, XSS, etc.
- 🔓 **Configuration issues**: Insecure settings

### Security Goals

✅ **Zero Critical Vulnerabilities**: No critical CVEs in production  
✅ **< 5 High Severity**: Minimal high severity issues  
✅ **No Secrets in Code**: Credentials managed securely  
✅ **OWASP Top 10**: Compliance with OWASP standards  
✅ **Regular Scanning**: Weekly automated scans  

---

## 🛠️ Security Tools

### 1. Trivy

**Purpose**: Container image vulnerability scanning

**Features**:
- Detects CVEs in OS packages
- Scans application dependencies
- Configuration issues
- Fast (< 1 min per image)
- SARIF output for GitHub Security

**Usage**:
```bash
trivy image myapp:latest
trivy image --severity CRITICAL,HIGH myapp:latest
trivy image --format sarif -o results.sarif myapp:latest
```

---

### 2. npm audit

**Purpose**: Frontend dependency vulnerabilities

**Features**:
- Built into npm
- Checks npm registry for known CVEs
- Automatic fix suggestions
- JSON output

**Usage**:
```bash
cd apps/frontend
npm audit
npm audit --audit-level=moderate
npm audit fix
npm audit --json > audit-results.json
```

---

### 3. Safety & pip-audit

**Purpose**: Python dependency vulnerabilities

**Safety**:
```bash
safety check -r requirements.txt
safety check --json --output safety-report.json
```

**pip-audit**:
```bash
pip-audit -r requirements.txt
pip-audit --format json > pip-audit.json
```

---

### 4. Gitleaks

**Purpose**: Secrets scanning in Git history

**Features**:
- Detects API keys, passwords, tokens
- Configurable rules (`.gitleaks.toml`)
- Scans full Git history
- Fast (< 30 seconds)

**Usage**:
```bash
gitleaks detect --source . --verbose
gitleaks detect --report-path gitleaks-report.json
```

**Custom Rules** (`.gitleaks.toml`):
```toml
[[rules]]
id = "azure-storage-key"
description = "Azure Storage Account Key"
regex = '''(?i)azure.*(?:=|:).*([a-z0-9/\+]{86}==)'''
tags = ["key", "Azure"]
```

---

### 5. TruffleHog

**Purpose**: Alternative secrets scanner

**Features**:
- High entropy detection
- Verified secrets only
- GitHub integration

**Usage**:
```bash
trufflehog git file://. --only-verified
```

---

### 6. CodeQL

**Purpose**: Semantic code analysis (SAST)

**Features**:
- Deep code understanding
- Security & quality queries
- GitHub integration
- Python & JavaScript support

**Queries**:
- `security-extended`: Enhanced security checks
- `security-and-quality`: Security + code quality

---

### 7. Semgrep

**Purpose**: SAST with custom rules

**Features**:
- Fast pattern matching
- Multiple languages
- Pre-built rulesets
- Custom rules

**Rulesets**:
- `p/security-audit`: General security
- `p/owasp-top-ten`: OWASP Top 10
- `p/secrets`: Secret detection
- `p/python`: Python-specific
- `p/javascript`: JS-specific

**Usage**:
```bash
semgrep --config="p/security-audit" .
semgrep --config="p/owasp-top-ten" --json > semgrep.json
```

---

### 8. Docker Bench Security

**Purpose**: Docker host security configuration

**Features**:
- CIS Docker Benchmark
- Host configuration checks
- Container runtime checks

**Usage**:
```bash
git clone https://github.com/docker/docker-bench-security.git
cd docker-bench-security
sudo sh docker-bench-security.sh
```

---

### 9. OWASP ZAP

**Purpose**: Dynamic application security testing (DAST)

**Features**:
- API scanning
- Active & passive scans
- Baseline scan mode
- HTML & JSON reports

**Usage**:
```bash
cd tests/security
./run-zap-scan.sh http://localhost:8000
```

---

## 🐳 Container Scanning (Trivy)

### Scanning All Services

```bash
# Scan all 13 services
for service in gateway citizen ingestion metadata transfer mintic_client signature sharing notification read_models auth transfer_worker frontend; do
  echo "Scanning $service..."
  
  if [ "$service" = "frontend" ]; then
    docker build -t $service:test -f apps/frontend/Dockerfile apps/frontend
  else
    docker build -t $service:test -f services/$service/Dockerfile services/$service
  fi
  
  trivy image --severity CRITICAL,HIGH $service:test
done
```

### CI/CD Integration

**Workflow**: `.github/workflows/security-scan.yml`

**Matrix Strategy**:
```yaml
strategy:
  matrix:
    service: [gateway, citizen, ingestion, ...]
```

**Runs**:
- Build image
- Scan with Trivy
- Upload SARIF to GitHub Security
- Human-readable output

---

## 📦 Dependency Audit

### Frontend (npm audit)

```bash
cd apps/frontend

# Audit
npm audit

# Fix automatically
npm audit fix

# Force fix (breaking changes)
npm audit fix --force

# Audit specific level
npm audit --audit-level=high
```

**Common Vulnerabilities**:
- Prototype pollution
- ReDoS (Regular Expression DoS)
- XSS in dependencies
- Path traversal

**Resolution**:
```bash
# Update to latest
npm update

# Update specific package
npm update <package-name>

# Use overrides (package.json)
"overrides": {
  "vulnerable-package": "^2.0.0"
}
```

---

### Backend (Safety & pip-audit)

```bash
# For each service
cd services/citizen

# Export from Poetry
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Scan with Safety
safety check --file requirements.txt

# Scan with pip-audit
pip-audit -r requirements.txt
```

**Common Vulnerabilities**:
- SQL injection (in ORMs)
- XML external entity (XXE)
- Deserialization vulnerabilities
- Insecure randomness

**Resolution**:
```bash
# Update in pyproject.toml
poetry update <package-name>

# Or pin specific version
poetry add <package-name>@^2.0.0
```

---

## 🔑 Secrets Scanning

### Gitleaks Configuration

**File**: `.gitleaks.toml`

**Custom Rules**:
```toml
[[rules]]
id = "azure-storage-key"
description = "Azure Storage Account Key"
regex = '''azure.*([a-z0-9/\+]{86}==)'''
tags = ["key", "Azure"]

[[rules]]
id = "postgresql-connection-string"
description = "PostgreSQL Connection String"
regex = '''postgresql://[^:]+:[^@]+@[^/]+/[^\\s]+'''
tags = ["connection-string", "database"]
```

**Allowlist**:
```toml
[allowlist]
paths = [
  '''.*test.*''',
  '''.*example.*''',
]

regexes = [
  '''test-api-key''',
  '''dummy-secret''',
]
```

---

### Running Gitleaks

```bash
# Detect secrets
gitleaks detect --source . --verbose

# Generate report
gitleaks detect --report-path gitleaks-report.json

# Scan specific commit range
gitleaks detect --log-opts="HEAD~10..HEAD"
```

---

### Preventing Secrets

**Pre-commit Hook**:
```bash
#!/bin/sh
# .git/hooks/pre-commit

gitleaks protect --staged --verbose
```

**Best Practices**:
1. ✅ Use environment variables
2. ✅ Azure Key Vault for production
3. ✅ `.env.example` with dummy values
4. ✅ `.gitignore` for `.env` files
5. ❌ Never commit real credentials

---

## 🛡️ SAST (Static Analysis)

### CodeQL

**Workflow**: Integrated in `.github/workflows/security-scan.yml`

**Languages**: Python, JavaScript

**Queries**:
- `security-extended`: Enhanced security
- `security-and-quality`: Security + quality

**Results**: GitHub Security tab

---

### Semgrep

**Running Semgrep**:
```bash
# Security audit
semgrep --config="p/security-audit" .

# OWASP Top 10
semgrep --config="p/owasp-top-ten" .

# Custom rules
semgrep --config=custom-rules.yaml .

# Output formats
semgrep --config="p/security-audit" --json > results.json
semgrep --config="p/security-audit" --sarif > results.sarif
```

**Common Findings**:
- SQL injection
- XSS vulnerabilities
- Hardcoded secrets
- Insecure deserialization
- Path traversal
- Command injection

---

## 🔓 DAST (Dynamic Analysis)

### OWASP ZAP Baseline Scan

**Configuration**: `tests/security/zap-baseline.conf`

**Excluded URLs**:
```
-config globalexcludeurl.url_list.url\(0\).regex='.*/metrics.*'
-config globalexcludeurl.url_list.url\(1\).regex='.*/health.*'
```

**Running ZAP**:
```bash
cd tests/security

# Run baseline scan
./run-zap-scan.sh http://localhost:8000

# Results
cat reports/zap-baseline-report.html
cat reports/zap-baseline-report.json
```

**Alert Levels**:
- 🔴 **High**: Definite vulnerability
- 🟠 **Medium**: Probable vulnerability
- 🟡 **Low**: Possible vulnerability
- 🟢 **Informational**: Not a vulnerability

---

## 🔄 Security Workflow

### GitHub Actions

**File**: `.github/workflows/security-scan.yml`

**Trigger**:
- Push to `master`/`main`
- Pull requests
- Schedule: Weekly (Monday 3 AM UTC)
- Manual dispatch

**Jobs**:

1. **trivy-scan**: Container scanning (matrix: 13 services)
2. **dependency-audit**: npm + Safety + pip-audit
3. **secrets-scan**: Gitleaks + TruffleHog
4. **codeql-analysis**: Python + JavaScript SAST
5. **docker-bench**: Docker security benchmark
6. **sast-semgrep**: Semgrep SAST
7. **generate-report**: Consolidated security report

**Artifacts**:
- Trivy SARIF (uploaded to GitHub Security)
- Dependency audit results (30 days)
- Docker Bench results (30 days)
- Security report (90 days)

---

## 🚀 Running Scans

### Local Scan (Quick)

```bash
# 1. Container scan
docker build -t gateway:test -f services/gateway/Dockerfile services/gateway
trivy image gateway:test

# 2. Dependency audit
cd apps/frontend && npm audit
cd services/citizen && safety check

# 3. Secrets scan
gitleaks detect --source . --verbose

# 4. SAST
semgrep --config="p/security-audit" .
```

---

### Local Scan (Full)

```bash
# Run full security audit
./scripts/run-security-audit.sh
```

---

### CI/CD Scan

```bash
# GitHub Actions
# Automatic on push/PR

# Manual trigger
gh workflow run security-scan.yml
```

---

## 📊 Security Report

### Generated Report

**Script**: `scripts/generate-security-report.py`

**Sections**:
1. **Executive Summary**: Critical/High/Medium/Low counts
2. **Container Vulnerabilities**: Per-service breakdown
3. **Frontend Dependencies**: npm audit results
4. **Backend Dependencies**: Safety results
5. **Recommendations**: Prioritized action items
6. **Next Steps**: Remediation plan

**Example Output**:
```markdown
# 🔒 Security Scan Report

## 📊 Executive Summary

- **Critical**: 0 🔴
- **High**: 2 🟠
- **Medium**: 5 🟡
- **Low**: 12 🟢

**Status**: 🟡 Some issues found - Review recommended

## 🐳 Container Vulnerabilities (Trivy)

| Service | Vulnerabilities | Status |
|---------|----------------|--------|
| gateway | 2 | ⚠️ |
| citizen | 0 | ✅ |
| ingestion | 1 | ⚠️ |
...
```

---

## ✅ Best Practices

### DO ✅

1. **Run scans on every PR**
   ```yaml
   on:
     pull_request:
       branches: [master, main]
   ```

2. **Fix critical issues immediately**
   ```bash
   # Update vulnerable package
   npm update vulnerable-package
   ```

3. **Use `.trivyignore` for known issues**
   ```
   # CVE-2023-12345 expires:2024-12-31
   # Reason: False positive, vendor confirmed not exploitable
   CVE-2023-12345
   ```

4. **Rotate secrets regularly**
   ```bash
   # Every 90 days
   az keyvault secret set-attributes --expires "2024-12-31"
   ```

5. **Monitor GitHub Security tab**
   ```
   Settings → Security → Code scanning alerts
   ```

### DON'T ❌

1. **Don't ignore security alerts**
   ```bash
   # Bad: Ignoring without justification
   ```

2. **Don't commit secrets**
   ```bash
   # Bad: API key in code
   API_KEY = "sk_live_12345"
   
   # Good: Environment variable
   API_KEY = os.getenv("API_KEY")
   ```

3. **Don't use outdated base images**
   ```dockerfile
   # Bad
   FROM python:3.8
   
   # Good
   FROM python:3.13-slim
   ```

4. **Don't run containers as root**
   ```dockerfile
   # Good
   USER nonroot
   ```

---

## 📚 Referencias

- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [OWASP ZAP](https://www.zaproxy.org/)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [Semgrep](https://semgrep.dev/)
- [CodeQL](https://codeql.github.com/)
- [Docker Bench Security](https://github.com/docker/docker-bench-security)

---

## ✅ Resumen

**Security Audit Suite**:
- ✅ Container scanning (Trivy, 13 services)
- ✅ Dependency audit (npm, Safety, pip-audit)
- ✅ Secrets scanning (Gitleaks, TruffleHog)
- ✅ SAST (CodeQL, Semgrep)
- ✅ DAST (OWASP ZAP)
- ✅ Docker Bench Security
- ✅ CI/CD workflow (7 jobs)
- ✅ Security report generator
- ✅ GitHub Security integration

**Scan Frequency**:
- Every PR
- Every push to master
- Weekly schedule
- Manual on-demand

**Tools**:
- 9 security tools integrated
- Comprehensive coverage
- Automated remediation suggestions

**Estado**: 🟢 Production-ready

---

**Generado**: 2025-10-13 09:15  
**Autor**: Manuel Jurado  
**Versión**: 1.0

