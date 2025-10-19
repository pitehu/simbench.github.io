"""
process_simbench_results.py

Convert raw results produced by generate_answers.py (pickle/CSV/DataFrame) into
the JSON schema expected by the website explorer.

Usage:
  python process_simbench_results.py --input path/to/results.pkl --output website/data/results.json

This script attempts to be robust to small schema differences:
- Detects Response_Distribution as a dict or a list and maps indices to labels.
- Detects human_answer as counts (sum>1) or probabilities and normalizes to probabilities.
- Uses answer options from auxiliary/answer_options or falls back to A,B,C... mapping.
- Maps depth numeric -> split label and maps TV_rescaled -> SimBench_Score when available.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import numpy as np


def is_null_or_na(x):
    """Safely check if value is null/NA, handling arrays."""
    if x is None:
        return True
    try:
        # For scalars and compatible types
        if pd.isna(x):
            return True
    except (ValueError, TypeError):
        # pd.isna() raises ValueError for arrays
        # Check if it's an array-like with all NaN
        try:
            return np.all(pd.isna(x))
        except:
            pass
    return False


def safe_to_list(x):
    if is_null_or_na(x):
        return None
    if isinstance(x, list):
        return x
    if isinstance(x, (str,)):
        try:
            v = json.loads(x)
            if isinstance(v, list):
                return v
        except Exception:
            return None
    return None


def normalize_prob_dict(d: Dict[str, float]) -> Dict[str, float]:
    # ensure non-negative and sum to 1 (if total>0)
    if not d:
        return {}
    cleaned = {k: max(0.0, float(v) if v is not None else 0.0) for k, v in d.items()}
    s = sum(cleaned.values())
    if s <= 0:
        # fallback to uniform
        n = len(cleaned) or 1
        return {k: 1.0 / n for k in cleaned}
    return {k: v / s for k, v in cleaned.items()}


def list_to_label_dict(lst: List[float], labels: List[str]) -> Dict[str, float]:
    # Map list of probabilities/counts to labels; if length mismatch, truncate/pad
    n = max(len(lst), len(labels))
    # pad lst with zeros if needed
    values = list(lst) + [0.0] * max(0, len(labels) - len(lst))
    # if there are more values than labels, create numeric labels
    effective_labels = labels + [f'opt{i}' for i in range(len(labels), len(values))]
    d = {lab: float(val) for lab, val in zip(effective_labels, values)}
    return normalize_prob_dict(d)


def infer_labels_from_aux(aux: Any) -> List[str]:
    # auxiliary may contain answer options or the correct answer value; try some heuristics
    if isinstance(aux, dict):
        if 'answer_options' in aux and isinstance(aux['answer_options'], list):
            return [str(x) for x in aux['answer_options']]
        if 'options' in aux and isinstance(aux['options'], list):
            return [str(x) for x in aux['options']]
    return []


def calculate_entropy_category(entropy_value: float) -> str:
    """Categorize human agreement based on normalized entropy."""
    if is_null_or_na(entropy_value):
        return 'Unknown'
    try:
        entropy_value = float(entropy_value)
    except (ValueError, TypeError):
        return 'Unknown'
    if entropy_value < 0.33:
        return 'High'
    elif entropy_value < 0.66:
        return 'Medium'
    else:
        return 'Low'


def process_row(row: pd.Series) -> Dict[str, Any]:
    # Columns we definitely want in the website JSON
    out: Dict[str, Any] = {}
    out['dataset_name'] = row.get('dataset_name') if 'dataset_name' in row else row.get('dataset')
    out['input_template'] = row.get('input_template') or row.get('prompt') or ''
    out['group_prompt_template'] = row.get('group_prompt_template') or ''
    out['group_prompt_variable_map'] = row.get('group_prompt_variable_map') or {}
    
    # Safely get group_size
    gs = row.get('group_size')
    try:
        out['group_size'] = int(gs) if not is_null_or_na(gs) else None
    except (ValueError, TypeError):
        out['group_size'] = None
    
    out['Model'] = row.get('Model') or row.get('model') or row.get('Model_Name')
    out['Prompt_Method'] = row.get('Prompt_Method') or row.get('prompt_method')
    
    # System Prompt (NEW - important for transparency)
    # Check multiple possible field names
    system_prompt = row.get('System_Prompt') or row.get('system_prompt') or row.get('System_prompt') or row.get('SystemPrompt')
    out['System_Prompt'] = str(system_prompt) if not is_null_or_na(system_prompt) else ''
    
    # Subset field (NEW - SimBenchPop vs SimBenchGrouped)
    # First try direct Subset field, then derive from depth
    subset = row.get('Subset') or row.get('subset')
    if is_null_or_na(subset) or subset == '':
        # Try to derive from depth field
        depth_val = row.get('depth')
        if not is_null_or_na(depth_val):
            try:
                depth_int = int(depth_val)
                depth_map = {0: 'SimBenchPop', 1: 'SimBenchGrouped'}
                subset = depth_map.get(depth_int, '')
            except (ValueError, TypeError):
                if isinstance(depth_val, str):
                    subset = depth_val
                else:
                    subset = ''
        else:
            subset = ''
    out['Subset'] = str(subset) if subset else ''
    
    # Human Normalized Entropy (NEW - for agreement filtering)
    entropy_val = row.get('Human_Normalized_Entropy')
    if not is_null_or_na(entropy_val):
        try:
            entropy_val = float(entropy_val)
            out['Human_Normalized_Entropy'] = entropy_val
            out['Human_Agreement'] = calculate_entropy_category(entropy_val)
        except (ValueError, TypeError):
            out['Human_Normalized_Entropy'] = None
            out['Human_Agreement'] = 'Unknown'
    else:
        out['Human_Normalized_Entropy'] = None
        out['Human_Agreement'] = 'Unknown'

    # Try to find answer option labels and their text
    labels = []
    option_texts = []
    
    # First check if answer_options column exists
    ao = row.get('answer_options')
    if not is_null_or_na(ao):
        if isinstance(ao, list):
            labels = [str(x) for x in ao]
            # If answer_options contains the full text, use it
            # Otherwise we'll extract from input_template below
            if labels and not any(len(x) == 1 for x in labels):
                option_texts = labels
                # Extract just the letters for labels
                labels = [chr(ord('A') + i) for i in range(len(option_texts))]
        else:
            try:
                parsed = [str(x) for x in json.loads(ao)]
                labels = parsed
                if labels and not any(len(x) == 1 for x in labels):
                    option_texts = labels
                    labels = [chr(ord('A') + i) for i in range(len(option_texts))]
            except Exception:
                labels = []
    
    # Try to infer from input_template (count (A), (B), (C), (D) patterns)
    # Also extract the option text that follows the letter
    if not labels or not option_texts:
        template = row.get('input_template')
        if not is_null_or_na(template):
            template = str(template)
            # Extract both letter and text: (A): Some text
            import re
            # Pattern matches (A): text up to next option or end
            option_pattern = r'\(([A-Z])\):\s*([^\n(]+?)(?=\s*\([A-Z]\):|$)'
            matches = re.findall(option_pattern, template, re.MULTILINE | re.DOTALL)
            if matches:
                if not labels:
                    labels = [m[0] for m in matches]
                if not option_texts:
                    option_texts = [m[1].strip() for m in matches]

    # check auxiliary field
    if not labels:
        aux = row.get('auxiliary')
        if not is_null_or_na(aux):
            try:
                if isinstance(aux, str):
                    aux = json.loads(aux)
                labels = infer_labels_from_aux(aux)
            except Exception:
                labels = []

    # default simple labels A,B,C...
    if not labels:
        labels = [chr(ord('A') + i) for i in range(int(row.get('Num_Options') or row.get('Num_Choices') or 4))]

    # Human answer: may be dict-like, list-like, or counts
    # NEW: Always normalize to ensure it's a probability distribution
    human = {}
    ha = row.get('human_answer')
    if not is_null_or_na(ha):
        if isinstance(ha, dict):
            # If sum >> 1, these are counts, normalize them
            total = sum(ha.values())
            if total > 1.5:  # Assume counts if sum significantly > 1
                human = normalize_prob_dict(ha)
            else:
                # Already probabilities, just ensure normalized
                human = normalize_prob_dict(ha)
        else:
            # try parse string or list
            lst = safe_to_list(ha)
            if lst is not None:
                # if numbers look like counts (sum>1) normalize
                s = sum([float(x) for x in lst])
                if s > 0:
                    human = list_to_label_dict(lst, labels)
            else:
                # if it's a scalar or single label, create one-hot
                try:
                    # try JSON
                    parsed = json.loads(ha)
                    if isinstance(parsed, dict):
                        human = normalize_prob_dict(parsed)
                except Exception:
                    # fallback: treat as single label string
                    hv = str(ha)
                    human = {lab: 1.0 if lab == hv else 0.0 for lab in labels}

    # Response_Distribution or Predicted_Distribution: model predicted distribution
    # NEW: Handle both list format [0.05, 0.1, 0.15, 0.7] and dict format
    model_dist = {}
    rd_field = None
    
    pd_val = row.get('Predicted_Distribution')
    rd_val = row.get('Response_Distribution')
    
    if not is_null_or_na(pd_val):
        rd_field = pd_val
    elif not is_null_or_na(rd_val):
        rd_field = rd_val
    
    if rd_field is not None:
        if isinstance(rd_field, dict):
            model_dist = normalize_prob_dict(rd_field)
        elif isinstance(rd_field, list):
            # Map list to labels: [0.05, 0.1, 0.15, 0.7] -> {A: 0.05, B: 0.1, C: 0.15, D: 0.7}
            model_dist = list_to_label_dict(rd_field, labels)
        else:
            lst = safe_to_list(rd_field)
            if lst is not None:
                model_dist = list_to_label_dict(lst, labels)
            else:
                # try parse json dict
                try:
                    parsed = json.loads(rd_field)
                    if isinstance(parsed, dict):
                        model_dist = normalize_prob_dict(parsed)
                    elif isinstance(parsed, list):
                        model_dist = list_to_label_dict(parsed, labels)
                except Exception:
                    model_dist = {}

    # If human or model empty, try to convert Human_Distribution/Model_Distribution etc.
    if not human:
        hd_val = row.get('Human_Distribution')
        if not is_null_or_na(hd_val):
            human = normalize_prob_dict(hd_val)
    if not model_dist:
        md_val = row.get('Model_Distribution')
        if not is_null_or_na(md_val):
            model_dist = normalize_prob_dict(md_val)

    # Ensure both have same keys: union of labels
    union_keys = list(dict.fromkeys(list(labels) + list(human.keys()) + list(model_dist.keys())))
    # Fill missing keys with zero then normalize
    human_full = {k: human.get(k, 0.0) for k in union_keys}
    model_full = {k: model_dist.get(k, 0.0) for k in union_keys}
    human_full = normalize_prob_dict(human_full)
    model_full = normalize_prob_dict(model_full)

    out['human_answer'] = human_full
    out['Response_Distribution'] = model_full
    
    # Store answer_options for display in the UI
    # Use extracted option texts if available, otherwise use labels
    if option_texts and len(option_texts) == len(union_keys):
        out['answer_options'] = option_texts
    else:
        out['answer_options'] = union_keys

    # Map depth to split name if present (and update Subset if it's empty)
    depth_val = row.get('depth')
    if not is_null_or_na(depth_val):
        try:
            depth_map = {0: 'SimBenchPop', 1: 'SimBenchGrouped'}
            out['depth'] = int(depth_val)
            split_name = depth_map.get(int(depth_val), str(depth_val))
            out['split'] = split_name
            # Update Subset if it wasn't set earlier
            if not out.get('Subset') or out['Subset'] == '':
                out['Subset'] = split_name
        except Exception:
            out['depth'] = depth_val

    # SimBench score: NEW - Handle range from -inf to 100
    # Try multiple column names in order of preference
    score_val = row.get('SimBench_Score')
    if not is_null_or_na(score_val):
        try:
            out['SimBench_Score'] = float(score_val)
        except (ValueError, TypeError):
            score_val = None
    
    if score_val is None or is_null_or_na(score_val):
        tv_val = row.get('TV_rescaled')
        if not is_null_or_na(tv_val):
            try:
                out['SimBench_Score'] = float(tv_val)
            except (ValueError, TypeError):
                pass
        else:
            tot_var = row.get('Total_Variation')
            if not is_null_or_na(tot_var):
                try:
                    out['SimBench_Score'] = float(tot_var)
                except (ValueError, TypeError):
                    out['SimBench_Score'] = None
            else:
                out['SimBench_Score'] = None

    # Keep original helpful fields
    aux_val = row.get('auxiliary')
    if not is_null_or_na(aux_val):
        try:
            aux = aux_val
            if isinstance(aux, str):
                aux = json.loads(aux)
            out['auxiliary'] = aux
        except Exception:
            out['auxiliary'] = aux_val

    # copy any other interesting fields (Model, Prompt_Method already present)
    for col in ['Sum_of_Probs', 'User_Prompt', 'input_variable_map']:
        val = row.get(col)
        if not is_null_or_na(val):
            out[col] = val

    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True, help='Path to input pickle/csv')
    parser.add_argument('--output', '-o', required=True, help='Path to output JSON file')
    parser.add_argument('--sample', '-s', type=int, default=None, 
                       help='Randomly sample N rows (useful for large datasets)')
    parser.add_argument('--max-rows', '-m', type=int, default=None,
                       help='Maximum number of rows to process (takes first N rows)')
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print('Input file not found:', inp)
        return

    # load with pandas
    if inp.suffix in ['.pkl', '.pickle']:
        df = pd.read_pickle(inp)
    else:
        # try CSV/TSV
        try:
            df = pd.read_csv(inp)
        except Exception as e:
            print('Could not read input file as CSV or pickle:', e)
            return

    original_rows = len(df)
    
    # Apply sampling/limiting if requested
    if args.sample and args.sample < original_rows:
        print(f"📊 Matched sampling: selecting {args.sample:,} questions from {original_rows:,} total rows...")
        
        # Identify unique question combinations (User_Prompt + System_Prompt)
        # Try different field name variations
        user_prompt_col = None
        for col in ['User_Prompt', 'user_prompt', 'input_template', 'prompt']:
            if col in df.columns:
                user_prompt_col = col
                break
        
        system_prompt_col = None
        for col in ['System_Prompt', 'system_prompt', 'SystemPrompt']:
            if col in df.columns:
                system_prompt_col = col
                break
        
        if user_prompt_col and system_prompt_col:
            # Create a unique question identifier
            df['_question_id'] = df[user_prompt_col].astype(str) + '|||' + df[system_prompt_col].astype(str)
            
            # Get unique question IDs
            unique_questions = df['_question_id'].unique()
            print(f"   Found {len(unique_questions):,} unique question combinations")
            
            # Sample questions (not individual rows)
            n_questions_to_sample = min(args.sample, len(unique_questions))
            sampled_questions = np.random.choice(unique_questions, size=n_questions_to_sample, replace=False)
            
            # Keep all rows that match the sampled questions (across all models)
            df = df[df['_question_id'].isin(sampled_questions)]
            df = df.drop(columns=['_question_id'])
            
            print(f"   Kept {len(df):,} rows across all models for {n_questions_to_sample:,} questions")
        else:
            print(f"   Warning: Could not find User_Prompt or System_Prompt columns for matched sampling")
            print(f"   Falling back to random row sampling...")
            df = df.sample(n=args.sample, random_state=42)
        
        df = df.reset_index(drop=True)
    elif args.max_rows and args.max_rows < original_rows:
        print(f"📊 Taking first {args.max_rows:,} rows from {original_rows:,} total rows...")
        df = df.head(args.max_rows)
    
    records = []
    total_rows = len(df)
    print(f"Processing {total_rows:,} rows...")
    
    failed_count = 0
    for idx, row in df.iterrows():
        try:
            rec = process_row(row)
            records.append(rec)
            
            # Progress reporting for large datasets
            if (idx + 1) % 10000 == 0:
                print(f"  Processed {idx + 1:,}/{total_rows:,} rows ({(idx+1)/total_rows*100:.1f}%)")
        except Exception as e:
            failed_count += 1
            if failed_count <= 10:  # Only show first 10 errors
                print(f'Warning: failed to process row {idx}: {e}')
            elif failed_count == 11:
                print(f'  ... suppressing further error messages ...')

    if failed_count > 0:
        print(f"\n⚠️  {failed_count} rows failed to process (out of {total_rows})")
        print(f"✓  Successfully processed {len(records)} rows")

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, 'w', encoding='utf8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f'Wrote {len(records)} records to {outp} (size: {outp.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
