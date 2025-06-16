#!/usr/bin/env python3
"""
Enhance Workflow Metadata with OpenAI
שיפור מטאדאטה של workflows באמצעות OpenAI כדי לקבל titles, descriptions ו-filenames אחידים ומובנים
"""

import json
import os
import time
from openai import OpenAI
from typing import Dict, Any, Optional
import argparse
from pathlib import Path

class WorkflowMetadataEnhancer:
    def __init__(self, api_key: str):
        """אתחול עם מפתח OpenAI API"""
        self.client = OpenAI(api_key=api_key)
        self.enhanced_count = 0
        self.error_count = 0
        self.results = []
        
    def create_enhancement_prompt(self, workflow_data: Dict[str, Any]) -> str:
        """יצירת prompt מפורט עבור OpenAI"""
        
        # חילוץ מידע על הworkflow
        workflow_content = workflow_data.get('content', {})
        nodes = workflow_content.get('nodes', [])
        connections = workflow_content.get('connections', {})
        workflow_id = workflow_data.get('id', '')
        
        # חילוץ שמות nodes ופעולות
        node_types = []
        node_names = []
        for node in nodes:
            node_type = node.get('type', '').replace('n8n-nodes-base.', '')
            node_name = node.get('name', '')
            if node_type:
                node_types.append(node_type)
            if node_name:
                node_names.append(node_name)
        
        # חילוץ המטאדאטה החדשה שלנו אם קיימת
        services = workflow_data.get('services', [])
        categories = workflow_data.get('categories', [])
        triggers = workflow_data.get('triggers', [])
        actions = workflow_data.get('actions', [])
        difficulty = workflow_data.get('difficulty', 'Unknown')
        setup_requirements = workflow_data.get('setup_requirements', [])
        
        # המרת התוכן לJSON מעוצב (מקוצר אם יותר מדי ארוך)
        content_str = json.dumps(workflow_content, indent=2, ensure_ascii=False)
        if len(content_str) > 3000:  # הגבלה לגודל סביר
            # נקצר ונציג רק מידע חשוב
            simplified_content = {
                "nodes": [{
                    "name": node.get('name', ''),
                    "type": node.get('type', '').replace('n8n-nodes-base.', ''),
                    "parameters": node.get('parameters', {}),
                    "position": node.get('position', [])
                } for node in nodes],
                "connections": connections
            }
            content_str = json.dumps(simplified_content, indent=2, ensure_ascii=False)
        
        prompt = f"""
# Task: Create N8N Workflow Metadata

You are creating metadata for workflow #{workflow_id} in a public N8N workflows library. Analyze the complete workflow structure below and create clear, user-friendly metadata that explains what this automation does.

## Complete Workflow Structure:
```json
{content_str}
```

## Our Analysis Summary:
**Workflow ID:** {workflow_id}
**Total Nodes:** {len(nodes)}
**Node Types:** {', '.join(set(node_types))}
**Node Names:** {', '.join(node_names)}

**Extracted Services:** {', '.join(services) if services else 'Not detected'}
**Categories:** {', '.join(categories) if categories else 'Not detected'}
**Triggers:** {', '.join(triggers) if triggers else 'Not detected'}
**Actions:** {', '.join(actions) if actions else 'Not detected'}
**Difficulty:** {difficulty}
**Setup Requirements:** {', '.join(setup_requirements) if setup_requirements else 'Not detected'}

## Context & Instructions:
- This is a public library of 2053 N8N automation workflows
- Users browse these to find workflow examples they can copy and use
- Analyze the complete workflow logic, connections, and parameters
- Focus on the business value and practical automation this provides
- Write for end-users who want to understand what gets automated

## Create These Fields:

### Title (max 80 characters):
- Clear, action-oriented description based on the actual workflow logic
- Start with a verb (e.g., "Automate", "Send", "Create", "Monitor", "Sync")
- Include the main services/platforms and key action
- User-friendly language that explains the business value
- Examples: 
  * "Send Slack notifications for new GitHub issues"
  * "Sync Airtable records with Google Calendar events"
  * "Automate invoice processing from Gmail to QuickBooks"

### Description (max 200 characters):
- Complete sentence explaining what the workflow accomplishes
- Mention the trigger event, main processing logic, and end result
- Include key platforms and explain the business benefit
- Based on the actual workflow flow and conditions you see
- Examples:
  * "Monitors GitHub repository for new issues and automatically sends formatted notifications to Slack with issue details and priority."
  * "Captures new form submissions from Typeform, filters positive responses, and logs qualified leads to Google Sheets for sales follow-up."

### Filename (max 60 characters):
- Start with workflow ID: "{workflow_id}_"
- Use underscores between words
- Include main action and primary services involved
- Reflect the actual workflow purpose you analyzed
- Examples:
  * "{workflow_id}_github_issues_to_slack"
  * "{workflow_id}_typeform_leads_to_sheets"
  * "{workflow_id}_gmail_invoices_to_quickbooks"

## Important Guidelines:
- Base your response on the COMPLETE workflow structure provided above
- Analyze the actual node connections, parameters, and logic flow
- Do NOT reference any existing title/description (ignore them completely)
- Focus on what this specific automation accomplishes for users
- Use simple, clear language that non-technical users understand
- Emphasize the business value and time-saving benefit

## Response Format:
Return ONLY a valid JSON object with exactly this structure:
{{
    "title": "Your new title here",
    "description": "Your new description here", 
    "filename": "Your new filename here"
}}

Do not include any other text, explanations, or formatting.
"""
        return prompt.strip()
    
    def enhance_single_workflow(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """שיפור metadata של workflow יחיד"""
        
        try:
            prompt = self.create_enhancement_prompt(workflow_data)
            
            print(f"🔄 Processing workflow {workflow_data.get('id', 'unknown')}...")
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # מודל חסכוני ויעיל
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3  # יצירתיות נמוכה לעקביות
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # ניסיון לפרסר JSON
            try:
                result = json.loads(result_text)
                
                # וולידציה של השדות
                if all(key in result for key in ['title', 'description', 'filename']):
                    # וולידציה של אורכים
                    if len(result['title']) <= 80 and len(result['description']) <= 200 and len(result['filename']) <= 60:
                        print(f"✅ Enhanced successfully")
                        return result
                    else:
                        print(f"⚠️ Length validation failed")
                        return None
                else:
                    print(f"⚠️ Missing required fields")
                    return None
                    
            except json.JSONDecodeError:
                print(f"⚠️ Invalid JSON response: {result_text[:100]}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None
    
    def enhance_all_workflows(self, workflows_dir: str, max_files: int = None, delay: float = 1.0) -> Dict[str, Any]:
        """שיפור כל ה-workflows"""
        
        print(f"🚀 Starting metadata enhancement...")
        print(f"📁 Workflows directory: {workflows_dir}")
        
        workflow_files = [f for f in os.listdir(workflows_dir) if f.endswith('.json')]
        
        if max_files:
            workflow_files = workflow_files[:max_files]
            print(f"🔢 Processing first {max_files} files for testing")
        
        print(f"📊 Total files to process: {len(workflow_files)}")
        
        results = {
            'enhanced_workflows': [],
            'errors': [],
            'summary': {
                'total_processed': 0,
                'successful': 0,
                'failed': 0
            }
        }
        
        for i, filename in enumerate(workflow_files, 1):
            file_path = os.path.join(workflows_dir, filename)
            
            try:
                # קריאת workflow
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                print(f"\n📝 [{i}/{len(workflow_files)}] {filename}")
                
                # שיפור metadata
                enhanced = self.enhance_single_workflow(workflow_data)
                
                if enhanced:
                    # שמירת התוצאה
                    results['enhanced_workflows'].append({
                        'original_file': filename,
                        'workflow_id': workflow_data.get('id'),
                        'original': {
                            'title': workflow_data.get('title', ''),
                            'description': workflow_data.get('description', ''),
                            'filename': workflow_data.get('filename', '')
                        },
                        'enhanced': enhanced
                    })
                    results['summary']['successful'] += 1
                    
                else:
                    results['errors'].append({
                        'file': filename,
                        'error': 'Enhancement failed'
                    })
                    results['summary']['failed'] += 1
                
                results['summary']['total_processed'] += 1
                
                # השהיה בין קריאות API
                if delay > 0:
                    time.sleep(delay)
                    
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                print(f"❌ {error_msg}")
                results['errors'].append({
                    'file': filename,
                    'error': error_msg
                })
                results['summary']['failed'] += 1
        
        return results
    
    def show_comparison_sample(self, results: Dict[str, Any], num_samples: int = 5):
        """הצגת דוגמאות השוואה בין metadata מקורי לחדש"""
        
        print(f"\n🔍 Sample Comparisons (first {num_samples} workflows):")
        print("=" * 100)
        
        for i, item in enumerate(results['enhanced_workflows'][:num_samples], 1):
            original = item['original']
            enhanced = item['enhanced']
            workflow_id = item['workflow_id']
            
            print(f"\n📝 {i}. Workflow #{workflow_id}")
            print("-" * 50)
            
            print(f"🔴 ORIGINAL Title: {original['title']}")
            print(f"🟢 NEW Title:      {enhanced['title']}")
            print()
            
            print(f"🔴 ORIGINAL Desc:  {original['description']}")
            print(f"🟢 NEW Desc:       {enhanced['description']}")
            print()
            
            print(f"🔴 ORIGINAL File:  {original['filename']}")
            print(f"🟢 NEW File:       {enhanced['filename']}")
            print()
            
            # הצגת שיפורים
            improvements = []
            if len(enhanced['title']) > len(original['title']):
                improvements.append("📏 Title expanded")
            if len(enhanced['description']) > len(original['description']):
                improvements.append("📝 Description detailed")
            if enhanced['filename'] != original['filename']:
                improvements.append("🏷️ Filename standardized")
                
            if improvements:
                print(f"✨ Improvements: {', '.join(improvements)}")
            
            print("=" * 50)

    def save_results(self, results: Dict[str, Any], output_file: str):
        """שמירת תוצאות לקובץ"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # הצגת דוגמאות השוואה
        if results['enhanced_workflows']:
            self.show_comparison_sample(results)
    
    def apply_enhancements(self, results: Dict[str, Any], workflows_dir: str, backup: bool = True):
        """החלת השיפורים על הקבצים המקוריים"""
        
        if backup:
            backup_dir = f"{workflows_dir}_backup_{int(time.time())}"
            print(f"📋 Creating backup in: {backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
        
        applied = 0
        
        for item in results['enhanced_workflows']:
            filename = item['original_file']
            enhanced = item['enhanced']
            file_path = os.path.join(workflows_dir, filename)
            
            try:
                # קריאת קובץ מקורי
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                # יצירת backup אם נדרש
                if backup:
                    backup_path = os.path.join(backup_dir, filename)
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                
                # עדכון metadata
                workflow_data['title'] = enhanced['title']
                workflow_data['description'] = enhanced['description']
                workflow_data['filename'] = enhanced['filename']
                
                # שמירת קובץ מעודכן
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                
                applied += 1
                print(f"✅ Applied enhancements to {filename}")
                
            except Exception as e:
                print(f"❌ Error applying to {filename}: {e}")
        
        print(f"\n🎉 Applied enhancements to {applied} files")

def main():
    parser = argparse.ArgumentParser(description='Enhance N8N workflow metadata using OpenAI')
    parser.add_argument('--api-key', required=True, help='OpenAI API key')
    parser.add_argument('--workflows-dir', default='workflows', help='Workflows directory')
    parser.add_argument('--output', default='enhanced_metadata.json', help='Output results file')
    parser.add_argument('--max-files', type=int, help='Maximum files to process (for testing)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls (seconds)')
    parser.add_argument('--apply', action='store_true', help='Apply enhancements to original files')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup when applying')
    
    args = parser.parse_args()
    
    enhancer = WorkflowMetadataEnhancer(args.api_key)
    
    # שיפור metadata
    results = enhancer.enhance_all_workflows(
        workflows_dir=args.workflows_dir,
        max_files=args.max_files,
        delay=args.delay
    )
    
    # שמירת תוצאות
    enhancer.save_results(results, args.output)
    
    # הצגת סיכום
    summary = results['summary']
    print(f"\n📊 Final Summary:")
    print(f"   Total processed: {summary['total_processed']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Success rate: {(summary['successful']/summary['total_processed']*100):.1f}%")
    
    # החלת שיפורים אם נדרש
    if args.apply:
        if input("\n❓ Apply enhancements to original files? (y/N): ").lower() == 'y':
            enhancer.apply_enhancements(
                results, 
                args.workflows_dir, 
                backup=not args.no_backup
            )

if __name__ == '__main__':
    main() 