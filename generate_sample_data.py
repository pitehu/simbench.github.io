#!/usr/bin/env python3
"""
Generate sample JSON data for testing the SimBench web explorer.

Usage:
    python generate_sample_data.py [output_file.json] [--num-questions N]
"""

import json
import random
import argparse
from pathlib import Path


def generate_sample_data(num_questions=100):
    """Generate sample SimBench results data."""
    
    datasets = [
        'OpinionQA', 'GlobalOpinionQA', 'AfroBarometer', 'LatinoBarometro',
        'ESS', 'ISSP', 'MoralMachine', 'Choices13k', 'ChaosNLI', 'Jester',
        'WisdomOfCrowds', 'OSPsychMGKT', 'OSPsychBig5', 'TISP'
    ]
    
    models = [
        'GPT-4.1', 'GPT-3.5-turbo', 'Claude-3-Opus', 'Claude-3-Sonnet',
        'Llama-3-70b', 'Llama-3-8b', 'Mistral-7b', 'Gemini-Pro'
    ]
    
    subsets = ['SimBenchPop', 'SimBenchGrouped']
    
    countries = [
        'United States', 'United Kingdom', 'Germany', 'France', 'Spain',
        'Brazil', 'Mexico', 'Kenya', 'South Africa', 'Nigeria',
        'India', 'China', 'Japan', 'Australia', 'Canada'
    ]
    
    age_groups = ['18-29', '30-49', '50-64', '65+']
    
    question_templates = [
        "Do you agree with the following statement: {}?",
        "In this scenario, what would you choose: {}?",
        "How would you rate your agreement with: {}?",
        "Which option best describes your view on {}?",
        "What is your opinion on the following: {}?",
    ]
    
    topics = [
        "government should regulate social media",
        "climate change is a serious threat",
        "economic growth should be prioritized over environmental protection",
        "immigration benefits the country",
        "artificial intelligence will create more jobs than it destroys",
        "universal healthcare should be provided by the government",
        "education should be free at all levels",
        "death penalty is justified for serious crimes",
        "same-sex marriage should be legal",
        "voting should be mandatory",
    ]
    
    data = []
    
    for i in range(num_questions):
        # Random question configuration
        num_options = random.choice([2, 3, 4, 5])
        if num_options == 2:
            options = ['A', 'B']
        elif num_options == 3:
            options = ['A', 'B', 'C']
        elif num_options == 4:
            options = ['A', 'B', 'C', 'D']
        else:
            options = ['A', 'B', 'C', 'D', 'E']
        
        # Generate human answer distribution
        human_answer = generate_distribution(options)
        
        # Generate model answer distribution (somewhat correlated with human)
        model_answer = generate_model_distribution(human_answer, correlation=0.7)
        
        # Calculate human entropy (normalized)
        entropy = calculate_normalized_entropy(human_answer)
        
        # Determine agreement category
        if entropy < 0.33:
            agreement = 'High'
        elif entropy < 0.66:
            agreement = 'Medium'
        else:
            agreement = 'Low'
        
        # Calculate SimBench Score (higher is better, -inf to 100)
        kl_div = calculate_kl_divergence(human_answer, model_answer)
        simbench_score = 100 - kl_div * 50
        
        # Random question text
        template = random.choice(question_templates)
        topic = random.choice(topics)
        question = template.format(topic)
        
        # Format as full question with options
        question_with_options = f"{question}\n\nOptions:\n"
        for opt in options:
            question_with_options += f"({opt}): Sample option {opt}\n"
        
        # Random demographic
        country = random.choice(countries)
        age = random.choice(age_groups)
        subset = random.choice(subsets)
        
        # System prompt varies by subset
        if subset == 'SimBenchGrouped':
            system_prompt = f"You are a group of individuals with these shared characteristics:\nYou are from {country}, aged {age}."
        else:
            system_prompt = "You are an Amazon Mechanical Turk worker from the United States."
        
        # Create data item
        item = {
            'index': i,
            'dataset_name': random.choice(datasets),
            'input_template': question_with_options,
            'System_Prompt': system_prompt,
            'Subset': subset,
            'Human_Normalized_Entropy': round(entropy, 4),
            'Human_Agreement': agreement,
            'human_answer': human_answer,
            'Response_Distribution': model_answer,
            'Model': random.choice(models),
            'SimBench_Score': round(simbench_score, 2),
            'Prompt_Method': random.choice(['token_prob', 'verbalized']),
            'group_size': random.randint(50, 2000)
        }
        
        data.append(item)
    
    return data


def generate_distribution(options):
    """Generate a random probability distribution over options."""
    # Use Dirichlet distribution for natural-looking probabilities
    alphas = [random.uniform(0.5, 5.0) for _ in options]
    probs = [random.random() for _ in alphas]
    total = sum(probs)
    probs = [p / total for p in probs]
    
    return {opt: prob for opt, prob in zip(options, probs)}


def calculate_normalized_entropy(distribution):
    """Calculate normalized entropy of a distribution (0 to 1)."""
    import math
    n = len(distribution)
    if n <= 1:
        return 0.0
    
    entropy = 0.0
    for prob in distribution.values():
        if prob > 0:
            entropy -= prob * math.log(prob)
    
    # Normalize by max entropy (uniform distribution)
    max_entropy = math.log(n)
    return entropy / max_entropy if max_entropy > 0 else 0.0


def calculate_kl_divergence(p, q):
    """Calculate KL divergence from q to p."""
    import math
    kl = 0.0
    eps = 1e-10
    
    for key in p:
        p_val = p[key]
        q_val = q.get(key, 0)
        if p_val > 0:
            kl += p_val * math.log((p_val + eps) / (q_val + eps))
    
    return max(0, kl)


def generate_model_distribution(human_answer, correlation=0.7):
    """Generate model distribution correlated with human distribution."""
    model_answer = {}
    
    for option, human_prob in human_answer.items():
        # Add noise to human probability
        noise = random.gauss(0, 0.1)
        model_prob = human_prob * correlation + (1 - correlation) * (1.0 / len(human_answer))
        model_prob = max(0.01, min(0.99, model_prob + noise))
        model_answer[option] = model_prob
    
    # Normalize
    total = sum(model_answer.values())
    model_answer = {k: v / total for k, v in model_answer.items()}
    
    return model_answer


def main():
    parser = argparse.ArgumentParser(
        description='Generate sample data for SimBench web explorer testing'
    )
    
    parser.add_argument(
        'output_file',
        type=str,
        nargs='?',
        default='sample_results.json',
        help='Output JSON file (default: sample_results.json)'
    )
    
    parser.add_argument(
        '--num-questions',
        type=int,
        default=100,
        help='Number of sample questions to generate (default: 100)'
    )
    
    args = parser.parse_args()
    
    print(f"Generating {args.num_questions} sample questions...")
    data = generate_sample_data(args.num_questions)
    
    output_path = Path(args.output_file)
    print(f"Saving to {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Generated {len(data)} sample questions")
    print(f"✓ Saved to {output_path}")
    print(f"✓ File size: {output_path.stat().st_size / 1024:.1f} KB")
    print("\nYou can now upload this file to the SimBench Results Explorer!")


if __name__ == '__main__':
    main()
