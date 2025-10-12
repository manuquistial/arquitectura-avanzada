#!/usr/bin/env python3
"""
Generate comprehensive security report from scan results
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def parse_trivy_results(artifacts_dir: Path) -> dict:
    """Parse Trivy scan results."""
    results = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0,
        'services': {}
    }
    
    trivy_files = list(artifacts_dir.glob('**/trivy-results-*.sarif'))
    
    for file in trivy_files:
        try:
            with open(file) as f:
                data = json.load(f)
                service = file.stem.replace('trivy-results-', '')
                
                vulnerabilities = []
                for run in data.get('runs', []):
                    for result in run.get('results', []):
                        severity = result.get('level', 'note')
                        vulnerabilities.append({
                            'severity': severity,
                            'message': result.get('message', {}).get('text', '')
                        })
                        
                        if severity == 'error':
                            results['critical'] += 1
                        elif severity == 'warning':
                            results['high'] += 1
                
                results['services'][service] = {
                    'vulnerabilities': len(vulnerabilities),
                    'details': vulnerabilities[:10]  # Top 10
                }
        except Exception as e:
            print(f"Error parsing {file}: {e}")
    
    return results


def parse_npm_audit(artifacts_dir: Path) -> dict:
    """Parse npm audit results."""
    results = {
        'vulnerabilities': 0,
        'critical': 0,
        'high': 0,
        'moderate': 0,
        'low': 0,
        'info': 0
    }
    
    npm_file = artifacts_dir / 'dependency-audit-results' / 'npm-audit.json'
    
    if npm_file.exists():
        try:
            with open(npm_file) as f:
                data = json.load(f)
                metadata = data.get('metadata', {})
                vulnerabilities = metadata.get('vulnerabilities', {})
                
                results['critical'] = vulnerabilities.get('critical', 0)
                results['high'] = vulnerabilities.get('high', 0)
                results['moderate'] = vulnerabilities.get('moderate', 0)
                results['low'] = vulnerabilities.get('low', 0)
                results['info'] = vulnerabilities.get('info', 0)
                results['vulnerabilities'] = sum(vulnerabilities.values())
        except Exception as e:
            print(f"Error parsing npm audit: {e}")
    
    return results


def parse_safety_results(artifacts_dir: Path) -> dict:
    """Parse Python safety check results."""
    results = {
        'vulnerabilities': 0,
        'services': defaultdict(int)
    }
    
    safety_files = list((artifacts_dir / 'dependency-audit-results').glob('safety-*.json'))
    
    for file in safety_files:
        try:
            with open(file) as f:
                data = json.load(f)
                service = file.stem.replace('safety-', '')
                
                vulns = len(data) if isinstance(data, list) else 0
                results['services'][service] = vulns
                results['vulnerabilities'] += vulns
        except Exception as e:
            print(f"Error parsing {file}: {e}")
    
    return results


def generate_report(artifacts_dir: Path, output_file: Path):
    """Generate comprehensive security report."""
    
    trivy = parse_trivy_results(artifacts_dir)
    npm = parse_npm_audit(artifacts_dir)
    safety = parse_safety_results(artifacts_dir)
    
    report = []
    report.append("# 🔒 Security Scan Report")
    report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append("\n---\n")
    
    # Summary
    report.append("## 📊 Executive Summary\n")
    
    total_critical = trivy['critical'] + npm['critical']
    total_high = trivy['high'] + npm['high']
    total_medium = trivy['medium'] + npm['moderate']
    
    report.append(f"- **Critical**: {total_critical} 🔴")
    report.append(f"- **High**: {total_high} 🟠")
    report.append(f"- **Medium**: {total_medium} 🟡")
    report.append(f"- **Low**: {trivy['low'] + npm['low']} 🟢")
    
    # Status
    if total_critical > 0:
        report.append("\n**Status**: ❌ CRITICAL ISSUES FOUND - Requires immediate action")
    elif total_high > 5:
        report.append("\n**Status**: ⚠️ HIGH SEVERITY ISSUES - Should be addressed soon")
    elif total_high > 0:
        report.append("\n**Status**: 🟡 Some issues found - Review recommended")
    else:
        report.append("\n**Status**: ✅ No critical or high severity issues")
    
    # Container Vulnerabilities
    report.append("\n\n## 🐳 Container Vulnerabilities (Trivy)\n")
    
    if trivy['services']:
        report.append("| Service | Vulnerabilities | Status |")
        report.append("|---------|----------------|--------|")
        
        for service, data in sorted(trivy['services'].items()):
            vuln_count = data['vulnerabilities']
            status = "✅" if vuln_count == 0 else "⚠️" if vuln_count < 5 else "❌"
            report.append(f"| {service} | {vuln_count} | {status} |")
    else:
        report.append("No container vulnerabilities scanned.")
    
    # Frontend Dependencies
    report.append("\n\n## 📦 Frontend Dependencies (npm audit)\n")
    
    if npm['vulnerabilities'] > 0:
        report.append(f"**Total vulnerabilities**: {npm['vulnerabilities']}\n")
        report.append(f"- Critical: {npm['critical']}")
        report.append(f"- High: {npm['high']}")
        report.append(f"- Moderate: {npm['moderate']}")
        report.append(f"- Low: {npm['low']}")
        report.append(f"- Info: {npm['info']}")
        
        if npm['critical'] > 0 or npm['high'] > 0:
            report.append("\n**Action Required**: Run `npm audit fix` to resolve issues.")
    else:
        report.append("✅ No vulnerabilities found in frontend dependencies.")
    
    # Backend Dependencies
    report.append("\n\n## 🐍 Backend Dependencies (Safety)\n")
    
    if safety['vulnerabilities'] > 0:
        report.append(f"**Total vulnerabilities**: {safety['vulnerabilities']}\n")
        
        if safety['services']:
            report.append("| Service | Vulnerabilities |")
            report.append("|---------|----------------|")
            
            for service, count in sorted(safety['services'].items()):
                report.append(f"| {service} | {count} |")
        
        report.append("\n**Action Required**: Update vulnerable dependencies.")
    else:
        report.append("✅ No vulnerabilities found in backend dependencies.")
    
    # Recommendations
    report.append("\n\n## 🛠️ Recommendations\n")
    
    if total_critical > 0:
        report.append("### Critical Priority")
        report.append("1. Address all CRITICAL vulnerabilities immediately")
        report.append("2. Update affected containers/dependencies")
        report.append("3. Run security scan again to verify fixes\n")
    
    if total_high > 0:
        report.append("### High Priority")
        report.append("1. Review and address HIGH severity issues")
        report.append("2. Update dependencies to latest stable versions")
        report.append("3. Consider implementing additional security controls\n")
    
    report.append("### General")
    report.append("1. Enable Dependabot for automatic dependency updates")
    report.append("2. Run security scans on every PR")
    report.append("3. Implement secret scanning in CI/CD")
    report.append("4. Regular security audits (weekly/monthly)")
    report.append("5. Keep base images up to date")
    
    # Next Steps
    report.append("\n\n## 📝 Next Steps\n")
    report.append("1. Review this report with the security team")
    report.append("2. Create tickets for critical and high severity issues")
    report.append("3. Update dependencies and rebuild containers")
    report.append("4. Re-run security scan to verify fixes")
    report.append("5. Document any accepted risks")
    
    # Footer
    report.append("\n---\n")
    report.append("**Report generated by**: Carpeta Ciudadana Security Pipeline")
    report.append(f"**Timestamp**: {datetime.now().isoformat()}")
    
    # Write report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n✅ Security report generated: {output_file}")
    
    # Print summary to console
    print("\n" + "=" * 60)
    print("📊 SECURITY SCAN SUMMARY")
    print("=" * 60)
    print(f"Critical: {total_critical}")
    print(f"High: {total_high}")
    print(f"Medium: {total_medium}")
    print(f"Low: {trivy['low'] + npm['low']}")
    print("=" * 60)
    
    # Exit with error if critical issues found
    if total_critical > 0:
        print("\n❌ CRITICAL VULNERABILITIES FOUND!")
        return 1
    elif total_high > 10:
        print("\n⚠️ Too many HIGH severity vulnerabilities!")
        return 1
    else:
        print("\n✅ Security scan passed!")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Generate security report')
    parser.add_argument('--artifacts', type=Path, default=Path('.'),
                      help='Path to artifacts directory')
    parser.add_argument('--output', type=Path, default=Path('security-report.md'),
                      help='Output file path')
    
    args = parser.parse_args()
    
    exit_code = generate_report(args.artifacts, args.output)
    exit(exit_code)


if __name__ == '__main__':
    main()

