#!/usr/bin/env python3
"""
Quick setup script for the SimBench website.
Generates sample data and provides instructions for local testing.
"""

import subprocess
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("SimBench Website Setup")
    print("=" * 60)
    print()
    
    # Check if we're in the website directory
    if not Path('index.html').exists():
        print("Error: Please run this script from the website directory")
        sys.exit(1)
    
    # Generate sample data
    print("Step 1: Generating sample data...")
    try:
        subprocess.run([sys.executable, 'generate_sample_data.py', 'data/sample_results.json', '--num-questions', '50'], check=True)
        print("✓ Sample data generated")
    except subprocess.CalledProcessError:
        print("! Warning: Could not generate sample data")
    except FileNotFoundError:
        # Create data directory if it doesn't exist
        Path('data').mkdir(exist_ok=True)
        subprocess.run([sys.executable, 'generate_sample_data.py', 'data/sample_results.json', '--num-questions', '50'], check=True)
        print("✓ Sample data generated")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("To test the website locally, run one of these commands:")
    print()
    print("  # Using Python:")
    print("  python -m http.server 8000")
    print()
    print("  # Using Node.js:")
    print("  npx http-server")
    print()
    print("Then open your browser to:")
    print("  http://localhost:8000")
    print()
    print("=" * 60)
    print("To deploy to GitHub Pages:")
    print("=" * 60)
    print()
    print("1. Push this website folder to your GitHub repository")
    print("2. Go to Settings → Pages")
    print("3. Select your branch and the /website folder")
    print("4. Save and wait for deployment")
    print()
    print("Your site will be available at:")
    print("  https://yourusername.github.io/repository-name/website/")
    print()
    print("=" * 60)


if __name__ == '__main__':
    main()
