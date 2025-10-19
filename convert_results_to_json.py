#!/usr/bin/env python3
"""
Convert SimBench results from pickle format to JSON for web viewing.

Usage:
    python convert_results_to_json.py input_file.pkl output_file.json
"""

import pickle
import json
import pandas as pd
import numpy as np
import argparse
import sys
from pathlib import Path


def convert_to_json_compatible(obj):
    """Convert numpy/pandas objects to JSON-compatible format."""
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {str(k): convert_to_json_compatible(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_compatible(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj


def pickle_to_json(pickle_path, json_path):
    """
    Convert a pickle file containing SimBench results to JSON format.
    
    Args:
        pickle_path: Path to input .pkl file
        json_path: Path to output .json file
    """
    print(f"Loading pickle file: {pickle_path}")
    
    try:
        # Load the pickle file
        with open(pickle_path, 'rb') as f:
            df = pd.read_pickle(f)
        
        print(f"Loaded {len(df)} records")
        
        # Convert to list of dictionaries
        data = []
        for idx, row in df.iterrows():
            # Extract relevant fields
            item = {
                'index': int(idx) if not pd.isna(idx) else idx,
                'dataset_name': str(row.get('dataset_name', '')) if pd.notna(row.get('dataset_name')) else '',
                'input_template': str(row.get('input_template', '')) if pd.notna(row.get('input_template')) else '',
                'group_prompt_template': str(row.get('group_prompt_template', '')) if pd.notna(row.get('group_prompt_template')) else '',
                'group_prompt_variable_map': convert_to_json_compatible(row.get('group_prompt_variable_map', {})),
                'human_answer': convert_to_json_compatible(row.get('human_answer', {})),
                'Response_Distribution': convert_to_json_compatible(row.get('Response_Distribution', {})),
                'Model': str(row.get('Model', '')) if pd.notna(row.get('Model')) else '',
                'Prompt_Method': str(row.get('Prompt_Method', '')) if pd.notna(row.get('Prompt_Method')) else '',
                'group_size': int(row.get('group_size', 0)) if pd.notna(row.get('group_size')) else 0,
            }
            
            # Add optional fields if they exist
            optional_fields = ['System_Prompt', 'User_Prompt', 'Sum_of_Probs', 'auxiliary']
            for field in optional_fields:
                if field in row and pd.notna(row[field]):
                    item[field] = convert_to_json_compatible(row[field])
            
            data.append(item)
        
        # Save as JSON
        print(f"Saving to JSON: {json_path}")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully converted {len(data)} records to JSON")
        print(f"✓ Output file: {json_path}")
        print(f"✓ File size: {Path(json_path).stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during conversion: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert SimBench pickle results to JSON for web viewing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  python convert_results_to_json.py results.pkl results.json
  
  # The output JSON can then be uploaded to the SimBench web explorer
        """
    )
    
    parser.add_argument('input_file', type=str, help='Input pickle file (.pkl)')
    parser.add_argument('output_file', type=str, nargs='?', help='Output JSON file (.json). If not provided, will use input filename with .json extension')
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"✗ Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    if not input_path.suffix == '.pkl':
        print(f"⚠ Warning: Input file doesn't have .pkl extension", file=sys.stderr)
    
    # Determine output file
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = input_path.with_suffix('.json')
    
    # Confirm overwrite if output exists
    if output_path.exists():
        response = input(f"Output file {output_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Conversion cancelled.")
            sys.exit(0)
    
    # Perform conversion
    success = pickle_to_json(input_path, output_path)
    
    if success:
        print("\n" + "="*60)
        print("Next steps:")
        print("1. Go to the SimBench Results Explorer")
        print("2. Upload the generated JSON file")
        print("3. Explore your model's predictions interactively!")
        print("="*60)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
