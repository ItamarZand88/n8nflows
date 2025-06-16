#!/usr/bin/env python3
"""
OpenAI Workflow Enhancer
Dedicated file for enhancing workflow metadata using OpenAI

Creates:
- title (clear and appropriate title)
- description (detailed description of functionality)
- filename (organized and understandable filename)

Created on 12/20/2024 by Itamar Zand
"""

import json
import os
import time
from openai import OpenAI
from typing import Dict, Any, Optional, List
import argparse
from pathlib import Path
from datetime import datetime
import sys

# ייבוא המיפוי שלנו
try:
    from n8n_mapping import N8NNodeMapper, load_workflow_file, save_workflow_file
except ImportError:
    print("❌ Error: Could not import n8n_mapping. Make sure n8n_mapping.py is in the same directory.")
    sys.exit(1)

class OpenAIWorkflowEnhancer:
    """Dedicated class for enhancing workflows with OpenAI"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """Initialize with API key and model"""
        
        # If no key provided, try to read from environment variable
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or provide it directly.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.mapper = N8NNodeMapper()
        
        # Variables for statistics
        self.enhanced_count = 0
        self.error_count = 0
        self.total_tokens_used = 0
        
        print(f"🤖 OpenAI Enhancer initialized with model: {model}")
    
    def create_enhancement_prompt(self, workflow_data: Dict[str, Any]) -> str:
        """Create detailed and professional prompt for OpenAI"""
        
        # Extract basic information
        workflow_content = workflow_data.get('content', {})
        nodes = workflow_content.get('nodes', [])
        connections = workflow_content.get('connections', {})
        workflow_id = workflow_data.get('id', 'unknown')
        
        # Extract metadata from our mapping
        metadata = self.mapper.extract_workflow_metadata(workflow_data)
        
        # Create organized list of nodes
        nodes_info = []
        for i, node in enumerate(nodes, 1):
            node_type = node.get('type', '').replace('n8n-nodes-base.', '')
            node_name = node.get('name', node_type)
            parameters = node.get('parameters', {})
            
            nodes_info.append(f"{i}. {node_name} ({node_type})")
            
            # Add important parameters
            if parameters:
                key_params = []
                for key, value in list(parameters.items())[:3]:  # Only first 3 parameters
                    if isinstance(value, str) and len(value) < 50:
                        key_params.append(f"{key}: {value}")
                if key_params:
                    nodes_info.append(f"   Parameters: {', '.join(key_params)}")
        
        # Create connections description
        connections_count = sum(len(conns) for conns in connections.values())
        flow_description = f"Workflow has {len(nodes)} nodes with {connections_count} connections"
        
        # Prepare the prompt
        prompt = f"""
# Task: Create Professional N8N Workflow Metadata

You are creating metadata for workflow #{workflow_id} in a professional N8N workflows library. This library serves developers and business users who want to automate processes.

## Workflow Structure Analysis:
**ID:** {workflow_id}
**Total Nodes:** {len(nodes)}
**Connections:** {connections_count}
**Flow:** {flow_description}

### Node Sequence:
{chr(10).join(nodes_info)}

### Our Analysis:
- **Platforms:** {', '.join(metadata.get('platforms', []))}
- **Categories:** {', '.join(metadata.get('categories', []))}
- **Triggers:** {', '.join(metadata.get('triggers', []))}
- **Actions:** {', '.join(metadata.get('actions', []))}
- **Difficulty:** {metadata.get('difficulty', 'Unknown')}

## Context:
- This is a public library with 2000+ automation workflows
- Users browse these to find examples for their automation needs
- Focus on business value and practical use cases
- Write for both technical and non-technical users

## Required Output:

### 1. Title (max 80 characters):
- Start with action verb (Automate, Send, Create, Monitor, Sync, etc.)
- Include main platforms/services involved
- Focus on the business outcome
- Examples:
  * "Automate Slack notifications for GitHub issues"
  * "Sync Google Sheets data with Airtable records"
  * "Send email alerts for Webhook events"

### 2. Description (max 200 characters):
- Complete sentence explaining the automation
- Mention trigger → process → outcome
- Include key benefits/use case
- Examples:
  * "Monitors GitHub for new issues and sends formatted Slack notifications with priority and assignment details."
  * "Captures form submissions from Typeform, filters qualified leads, and automatically adds them to Google Sheets."

### 3. Filename (max 60 characters):
- Format: "{workflow_id}_descriptive_name"
- Use underscores between words
- Include main action and primary service
- Examples:
  * "{workflow_id}_github_issues_to_slack"
  * "{workflow_id}_typeform_leads_to_sheets"
  * "{workflow_id}_webhook_email_alerts"

## Guidelines:
- Base response on the actual workflow structure above
- Use clear, professional language
- Emphasize automation benefits
- Make it findable/searchable
- Avoid technical jargon where possible

## Response Format:
Return ONLY a valid JSON object:
{{
    "title": "Your title here",
    "description": "Your description here",
    "filename": "Your filename here"
}}

No additional text or formatting.
"""
        return prompt.strip()
    
    def enhance_single_workflow(self, workflow_data: Dict[str, Any], 
                               delay: float = 1.0) -> Optional[Dict[str, str]]:
        """Enhance a single workflow with OpenAI"""
        
        workflow_id = workflow_data.get('id', 'unknown')
        
        try:
            print(f"🔄 Enhancing workflow {workflow_id} with OpenAI...")
            
            # Create the prompt
            prompt = self.create_enhancement_prompt(workflow_data)
            
            # Send to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at creating clear, professional metadata for automation workflows. Focus on business value and user intent."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.3,  # High consistency
                top_p=0.9
            )
            
            # Update statistics
            if hasattr(response, 'usage'):
                self.total_tokens_used += response.usage.total_tokens
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse the result
            try:
                result = json.loads(result_text)
                
                # Validation
                required_fields = ['title', 'description', 'filename']
                if not all(field in result for field in required_fields):
                    print(f"⚠️ Missing required fields in response")
                    return None
                
                # Check lengths
                if (len(result['title']) > 80 or 
                    len(result['description']) > 200 or 
                    len(result['filename']) > 60):
                    print(f"⚠️ Field length validation failed")
                    return None
                
                # Check that filename starts with workflow_id
                expected_prefix = f"{workflow_id}_"
                if not result['filename'].startswith(expected_prefix):
                    result['filename'] = expected_prefix + result['filename'].replace(expected_prefix, '')
                
                self.enhanced_count += 1
                print(f"✅ Enhanced successfully")
                
                # Add delay to avoid rate limiting
                if delay > 0:
                    time.sleep(delay)
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing error: {e}")
                print(f"Response was: {result_text[:200]}...")
                return None
                
        except Exception as e:
            print(f"❌ OpenAI API error: {str(e)}")
            self.error_count += 1
            return None
    
    def enhance_workflow_file(self, file_path: str, output_path: str = None, 
                             backup: bool = True) -> bool:
        """Enhance a single workflow file"""
        
        try:
            # Load the workflow
            workflow_data = load_workflow_file(file_path)
            workflow_id = workflow_data.get('id', 'unknown')
            
            print(f"📄 Processing file: {os.path.basename(file_path)}")
            
            # Check if fields already exist
            has_title = 'title' in workflow_data and workflow_data['title']
            has_description = 'description' in workflow_data and workflow_data['description']
            has_filename = 'filename' in workflow_data and workflow_data['filename']
            
            if has_title and has_description and has_filename:
                print(f"⏭️ Workflow {workflow_id} already has all required fields, skipping...")
                return True
            
            # Create backup if needed
            if backup and not output_path:
                backup_path = file_path + '.backup'
                if not os.path.exists(backup_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"💾 Created backup: {backup_path}")
            
            # Enhance with OpenAI
            enhancement = self.enhance_single_workflow(workflow_data)
            
            if not enhancement:
                print(f"❌ Failed to enhance workflow {workflow_id}")
                return False
            
            # Update the workflow
            workflow_data.update(enhancement)
            
            # Save
            output_file = output_path or file_path
            save_workflow_file(output_file, workflow_data)
            
            print(f"💾 Enhanced workflow saved to: {output_file}")
            self._display_enhancement_result(workflow_id, enhancement)
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing file {file_path}: {e}")
            return False
    
    def enhance_multiple_workflows(self, input_dir: str, output_dir: str = None,
                                 max_files: int = None, delay: float = 1.0,
                                 backup: bool = True) -> Dict[str, Any]:
        """Enhance multiple workflows"""
        
        print(f"🚀 Starting batch enhancement...")
        print(f"📁 Input directory: {input_dir}")
        
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Create output directory
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 Output directory: {output_dir}")
        
        # Collect files
        workflow_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
        
        if max_files:
            workflow_files = workflow_files[:max_files]
            print(f"🔢 Limited to {max_files} files")
        
        print(f"📊 Found {len(workflow_files)} workflow files")
        
        # Statistics
        results = {
            'total_files': len(workflow_files),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': datetime.now(),
            'enhancements': []
        }
        
        # Process each file
        for i, filename in enumerate(workflow_files, 1):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename) if output_dir else None
            
            print(f"\n[{i}/{len(workflow_files)}] Processing: {filename}")
            
            success = self.enhance_workflow_file(input_path, output_path, backup)
            
            results['processed'] += 1
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            # Display progress
            progress = (i / len(workflow_files)) * 100
            print(f"📈 Progress: {progress:.1f}% (✅ {results['successful']} | ❌ {results['failed']})")
        
        # Summary
        results['end_time'] = datetime.now()
        results['duration'] = results['end_time'] - results['start_time']
        results['tokens_used'] = self.total_tokens_used
        
        self._display_batch_summary(results)
        
        return results
    
    def _display_enhancement_result(self, workflow_id: str, enhancement: Dict[str, str]):
        """Display enhancement results"""
        print(f"📝 Enhancement Results for {workflow_id}:")
        print(f"   Title: {enhancement['title']}")
        print(f"   Description: {enhancement['description']}")
        print(f"   Filename: {enhancement['filename']}")
    
    def _display_batch_summary(self, results: Dict[str, Any]):
        """Display batch processing summary"""
        
        print(f"\n" + "="*60)
        print(f"🏁 Batch Enhancement Completed!")
        print(f"="*60)
        
        print(f"📊 Results Summary:")
        print(f"   Total Files: {results['total_files']}")
        print(f"   ✅ Successful: {results['successful']}")
        print(f"   ❌ Failed: {results['failed']}")
        print(f"   ⏭️ Skipped: {results['skipped']}")
        
        print(f"\n⏱️ Performance:")
        print(f"   Duration: {results['duration']}")
        print(f"   🤖 Tokens Used: {results['tokens_used']:,}")
        
        if results['successful'] > 0:
            avg_time = results['duration'].total_seconds() / results['successful']
            print(f"   Average per file: {avg_time:.1f} seconds")
        
        success_rate = (results['successful'] / results['total_files']) * 100
        print(f"   Success Rate: {success_rate:.1f}%")

def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description='Enhance N8N Workflows with OpenAI')
    parser.add_argument('input', help='Input workflow file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-k', '--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('-m', '--model', default='gpt-4o-mini', 
                       help='OpenAI model to use (default: gpt-4o-mini)')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    parser.add_argument('--delay', type=float, default=1.0, 
                       help='Delay between API calls in seconds (default: 1.0)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Do not create backup files')
    
    args = parser.parse_args()
    
    try:
        # Create enhancer
        enhancer = OpenAIWorkflowEnhancer(args.api_key, args.model)
        
        if os.path.isfile(args.input):
            # Single file
            success = enhancer.enhance_workflow_file(
                args.input, args.output, not args.no_backup
            )
            if not success:
                sys.exit(1)
        
        elif os.path.isdir(args.input):
            # Directory
            results = enhancer.enhance_multiple_workflows(
                args.input, args.output, args.max_files, 
                args.delay, not args.no_backup
            )
            
            if results['failed'] > 0:
                print(f"\n⚠️ Some files failed to process: {results['failed']}")
                sys.exit(1)
        
        else:
            print(f"❌ Error: {args.input} is not a valid file or directory")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 