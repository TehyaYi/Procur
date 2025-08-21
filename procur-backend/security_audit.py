#!/usr/bin/env python3
"""
Security Audit Script for Procur Backend
This script checks for common security issues and verifies security fixes.
"""

import os
import re
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SecurityAuditor:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.api_routes_dir = self.project_root / "procur" / "api" / "routes"
        self.core_dir = self.project_root / "procur" / "core"
        self.security_issues = []
        self.security_warnings = []
        self.security_passes = []
        
    def run_audit(self) -> Dict[str, List[str]]:
        """Run comprehensive security audit"""
        logger.info("🔒 Starting Security Audit...")
        
        # Check API routes security
        self._audit_api_routes()
        
        # Check core security
        self._audit_core_security()
        
        # Check dependencies
        self._audit_dependencies()
        
        # Check configuration
        self._audit_configuration()
        
        # Generate report
        return self._generate_report()
    
    def _audit_api_routes(self):
        """Audit API routes for security issues"""
        logger.info("📋 Auditing API routes...")
        
        if not self.api_routes_dir.exists():
            self.security_issues.append("API routes directory not found")
            return
        
        for route_file in self.api_routes_dir.glob("*.py"):
            if route_file.name == "__init__.py":
                continue
                
            self._audit_route_file(route_file)
    
    def _audit_route_file(self, route_file: Path):
        """Audit individual route file"""
        try:
            with open(route_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            filename = route_file.name
            
            # Check for manual permission checks instead of dependencies
            self._check_manual_permission_checks(content, filename)
            
            # Check for missing authentication
            self._check_missing_authentication(content, filename)
            
            # Check for proper error handling
            self._check_error_handling(content, filename)
            
            # Check for input validation
            self._check_input_validation(content, filename)
            
        except Exception as e:
            self.security_issues.append(f"Error auditing {route_file.name}: {e}")
    
    def _check_manual_permission_checks(self, content: str, filename: str):
        """Check for manual permission checks that should use dependencies"""
        patterns = [
            r'member_doc\.to_dict\(\)\.get\(\'role\'\)\s*!=\s*[\'"]admin[\'"]',
            r'if not member_doc\.exists or.*role.*!=.*admin',
            r'verify.*admin.*privileges',
            r'check.*admin.*status'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.security_warnings.append(
                    f"{filename}: Manual admin permission check detected - consider using require_group_admin dependency"
                )
    
    def _check_missing_authentication(self, content: str, filename: str):
        """Check for endpoints missing authentication"""
        # Look for router decorators without authentication
        router_patterns = [
            r'@router\.(get|post|put|delete|patch)\([^)]*\)\s*\n\s*async def [^(]*\([^)]*\):',
        ]
        
        for pattern in router_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                # Check if the function has authentication dependency
                func_start = match.end()
                func_end = content.find('\n\n', func_start)
                if func_end == -1:
                    func_end = len(content)
                
                func_content = content[func_start:func_end]
                if 'Depends(get_current_user)' not in func_content and 'Depends(require_group_admin' not in func_content and 'Depends(require_group_member' not in func_content:
                    # Check if it's a public endpoint (health check, etc.)
                    if 'health' not in func_content.lower() and 'public' not in func_content.lower():
                        self.security_warnings.append(
                            f"{filename}: Endpoint without authentication dependency detected"
                        )
    
    def _check_error_handling(self, content: str, filename: str):
        """Check for proper error handling"""
        # Look for bare except clauses
        if 'except:' in content:
            self.security_warnings.append(
                f"{filename}: Bare except clause detected - should specify exception types"
            )
        
        # Look for proper HTTP exception usage
        if 'HTTPException' in content and 'status_code=403' not in content:
            self.security_warnings.append(
                f"{filename}: Missing 403 Forbidden status codes for permission errors"
            )
    
    def _check_input_validation(self, content: str, filename: str):
        """Check for input validation"""
        # Look for file upload endpoints
        if 'UploadFile' in content:
            if 'validate_file' not in content and 'file_size' not in content:
                self.security_warnings.append(
                    f"{filename}: File upload endpoint without size validation"
                )
    
    def _audit_core_security(self):
        """Audit core security modules"""
        logger.info("🔐 Auditing core security...")
        
        # Check dependencies.py
        dependencies_file = self.core_dir / "dependencies.py"
        if dependencies_file.exists():
            self._audit_dependencies_file(dependencies_file)
        else:
            self.security_issues.append("dependencies.py not found")
        
        # Check firebase.py
        firebase_file = self.core_dir / "firebase.py"
        if firebase_file.exists():
            self._audit_firebase_file(firebase_file)
        else:
            self.security_issues.append("firebase.py not found")
    
    def _audit_dependencies_file(self, dependencies_file: Path):
        """Audit dependencies.py for security features"""
        try:
            with open(dependencies_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required security functions
            required_functions = [
                'require_group_admin',
                'require_group_member',
                'enforce_group_privacy',
                'get_current_user'
            ]
            
            for func in required_functions:
                if func not in content:
                    self.security_issues.append(f"Missing required security function: {func}")
                else:
                    self.security_passes.append(f"Security function found: {func}")
            
            # Check for proper error handling
            if 'HTTPException' in content and 'status_code=403' in content:
                self.security_passes.append("Proper permission error handling")
            else:
                self.security_warnings.append("Missing proper permission error handling")
                
        except Exception as e:
            self.security_issues.append(f"Error auditing dependencies.py: {e}")
    
    def _audit_firebase_file(self, firebase_file: Path):
        """Audit firebase.py for security features"""
        try:
            with open(firebase_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for security features
            security_features = [
                'verify_firebase_token',
                'blacklist_token',
                'revoke_user_tokens',
                'rate_limit'
            ]
            
            for feature in security_features:
                if feature in content:
                    self.security_passes.append(f"Security feature found: {feature}")
                else:
                    self.security_warnings.append(f"Missing security feature: {feature}")
                    
        except Exception as e:
            self.security_issues.append(f"Error auditing firebase.py: {e}")
    
    def _audit_dependencies(self):
        """Audit project dependencies for security"""
        logger.info("📦 Auditing dependencies...")
        
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self._audit_requirements_file(requirements_file)
        else:
            self.security_warnings.append("requirements.txt not found")
    
    def _audit_requirements_file(self, requirements_file: Path):
        """Audit requirements.txt for known vulnerable packages"""
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for known secure packages
            secure_packages = [
                'fastapi',
                'firebase-admin',
                'pydantic'
            ]
            
            for package in secure_packages:
                if package in content:
                    self.security_passes.append(f"Secure package found: {package}")
                else:
                    self.security_warnings.append(f"Package not found: {package}")
                    
        except Exception as e:
            self.security_issues.append(f"Error auditing requirements.txt: {e}")
    
    def _audit_configuration(self):
        """Audit configuration files for security"""
        logger.info("⚙️ Auditing configuration...")
        
        # Check for environment files
        env_files = list(self.project_root.glob(".env*"))
        if env_files:
            self.security_warnings.append(f"Environment files found: {[f.name for f in env_files]}")
        
        # Check for security config
        security_config = self.core_dir / "security_config.py"
        if security_config.exists():
            self.security_passes.append("Security configuration file found")
        else:
            self.security_warnings.append("Security configuration file not found")
    
    def _generate_report(self) -> Dict[str, List[str]]:
        """Generate security audit report"""
        logger.info("📊 Generating security report...")
        
        report = {
            "issues": self.security_issues,
            "warnings": self.security_warnings,
            "passes": self.security_passes
        }
        
        # Print summary
        logger.info(f"\n🔒 Security Audit Complete!")
        logger.info(f"✅ Passes: {len(self.security_passes)}")
        logger.info(f"⚠️  Warnings: {len(self.security_warnings)}")
        logger.info(f"❌ Issues: {len(self.security_issues)}")
        
        if self.security_issues:
            logger.error("\n❌ Security Issues Found:")
            for issue in self.security_issues:
                logger.error(f"  - {issue}")
        
        if self.security_warnings:
            logger.warning("\n⚠️  Security Warnings:")
            for warning in self.security_warnings:
                logger.warning(f"  - {warning}")
        
        if self.security_passes:
            logger.info("\n✅ Security Passes:")
            for passed in self.security_passes:
                logger.info(f"  - {passed}")
        
        return report

def main():
    """Main function to run security audit"""
    # Get project root (assuming script is in project root)
    project_root = Path(__file__).parent
    
    # Run audit
    auditor = SecurityAuditor(str(project_root))
    report = auditor.run_audit()
    
    # Exit with error code if issues found
    if report["issues"]:
        logger.error("Security audit failed with issues!")
        exit(1)
    elif report["warnings"]:
        logger.warning("Security audit completed with warnings.")
        exit(0)
    else:
        logger.info("Security audit passed successfully!")
        exit(0)

if __name__ == "__main__":
    main()
