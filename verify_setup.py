#!/usr/bin/env python3
"""
Verification script for SimBench website setup.
Checks that all required files exist and are properly configured.
"""

import sys
from pathlib import Path


def check_file(filepath, description):
    """Check if a file exists and return status."""
    path = Path(filepath)
    exists = path.exists()
    status = "✓" if exists else "✗"
    size = f"({path.stat().st_size} bytes)" if exists else ""
    print(f"{status} {description}: {filepath} {size}")
    return exists


def check_directory(dirpath, description):
    """Check if a directory exists."""
    path = Path(dirpath)
    exists = path.is_dir()
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {dirpath}")
    return exists


def main():
    print("=" * 70)
    print("SimBench Website Verification")
    print("=" * 70)
    print()
    
    all_good = True
    
    # Check HTML files
    print("📄 HTML Files:")
    all_good &= check_file("index.html", "Landing page")
    all_good &= check_file("explorer.html", "Results explorer")
    all_good &= check_file("datasets.html", "Datasets page")
    print()
    
    # Check CSS
    print("🎨 Stylesheets:")
    all_good &= check_directory("css", "CSS directory")
    all_good &= check_file("css/style.css", "Main stylesheet")
    print()
    
    # Check JavaScript
    print("⚡ JavaScript:")
    all_good &= check_directory("js", "JavaScript directory")
    all_good &= check_file("js/explorer.js", "Explorer script")
    print()
    
    # Check utilities
    print("🔧 Utility Scripts:")
    all_good &= check_file("convert_results_to_json.py", "Pickle to JSON converter")
    all_good &= check_file("generate_sample_data.py", "Sample data generator")
    all_good &= check_file("setup.py", "Setup script")
    print()
    
    # Check documentation
    print("📚 Documentation:")
    all_good &= check_file("README.md", "Main README")
    all_good &= check_file("DEPLOYMENT.md", "Deployment guide")
    all_good &= check_file("QUICKREF.md", "Quick reference")
    all_good &= check_file("PACKAGE_SUMMARY.md", "Package summary")
    print()
    
    # Check configuration
    print("⚙️  Configuration:")
    all_good &= check_file("_config.yml", "GitHub Pages config")
    all_good &= check_file(".gitignore", "Git ignore file")
    print()
    
    # Check optional files
    print("📋 Optional Files:")
    check_file("redirect.html", "Root redirect page")
    check_file(".github/workflows/deploy-pages.yml", "GitHub Actions workflow")
    print()
    
    # Validate HTML structure
    print("🔍 Validating HTML Structure:")
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
            checks = [
                ("<!DOCTYPE html>" in content, "DOCTYPE declaration"),
                ("<html" in content, "HTML tag"),
                ("<head>" in content, "Head section"),
                ("<body>" in content, "Body section"),
                ('href="css/style.css"' in content or 'href="./css/style.css"' in content, "CSS link"),
            ]
            for check, desc in checks:
                status = "✓" if check else "✗"
                print(f"{status} {desc}")
                all_good &= check
    except Exception as e:
        print(f"✗ Error reading index.html: {e}")
        all_good = False
    print()
    
    # Check JavaScript syntax (basic)
    print("🔍 Validating JavaScript:")
    try:
        with open("js/explorer.js", "r", encoding="utf-8") as f:
            content = f.read()
            checks = [
                ("document.addEventListener" in content, "DOM ready handler"),
                ("function" in content or "=>" in content, "Functions defined"),
                ("getElementById" in content, "DOM manipulation"),
            ]
            for check, desc in checks:
                status = "✓" if check else "✗"
                print(f"{status} {desc}")
    except Exception as e:
        print(f"⚠ Could not validate JavaScript: {e}")
    print()
    
    # Final summary
    print("=" * 70)
    if all_good:
        print("✓ All required files present and appear valid!")
        print()
        print("Next steps:")
        print("  1. Test locally: python -m http.server 8000")
        print("  2. Generate sample data: python generate_sample_data.py")
        print("  3. Deploy to GitHub Pages (see DEPLOYMENT.md)")
        print("=" * 70)
        return 0
    else:
        print("✗ Some files are missing or invalid.")
        print()
        print("Please ensure all files are in place before deploying.")
        print("See PACKAGE_SUMMARY.md for the complete file structure.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
