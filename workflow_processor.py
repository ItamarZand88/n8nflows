#!/usr/bin/env python3
"""
Workflow Processor - Process workflow JSON with N8N mapping
Takes a workflow JSON file and generates all relevant fields

Produces:
- platforms
- credentials requirements
- categories
- triggers & actions
- difficulty level
- nodes count

Created on 12/20/2024 by Itamar Zand
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
import argparse

# ייבוא המחלקה שלנו
try:
    from n8n_mapping import N8NNodeMapper, load_workflow_file, save_workflow_file
except ImportError:
    print("❌ Error: Could not import n8n_mapping. Make sure n8n_mapping.py is in the same directory.")
    sys.exit(1)

class WorkflowProcessor:
    """Process workflows with N8N mapping"""
    
    def __init__(self, mapping_file: str = "enhanced_n8n_mapping.json"):
        """Initialize with mapping file"""
        self.mapper = N8NNodeMapper(mapping_file)
        print(f"🔧 Workflow Processor initialized with mapping: {mapping_file}")
        
    def process_single_workflow(self, workflow_file: str, output_file: str = None) -> Dict[str, Any]:
        """Process a single workflow"""
        try:
            print(f"📄 Processing workflow: {workflow_file}")
            
            # Load the workflow
            workflow_data = load_workflow_file(workflow_file)
            workflow_id = workflow_data.get('id', 'unknown')
            
            print(f"🆔 Workflow ID: {workflow_id}")
            
            # Extract metadata using mapping
            metadata = self.mapper.extract_workflow_metadata(workflow_data)
            
            # Add metadata to workflow
            workflow_data.update(metadata)
            
            # Save if requested
            if output_file:
                save_workflow_file(output_file, workflow_data)
                print(f"💾 Saved enhanced workflow to: {output_file}")
            
            # Display results
            self._display_workflow_analysis(workflow_id, metadata, workflow_data)
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'metadata': metadata,
                'file_path': workflow_file
            }
            
        except Exception as e:
            print(f"❌ Error processing workflow: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': workflow_file
            }
    
    def process_multiple_workflows(self, input_dir: str, output_dir: str = None, 
                                 create_backup: bool = True) -> Dict[str, Any]:
        """Process multiple workflows"""
        
        print(f"📁 Processing workflows from: {input_dir}")
        
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # Create output directory if needed
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            print(f"📁 Output directory: {output_dir}")
        
        # Collect workflow files
        workflow_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
        
        if not workflow_files:
            print("⚠️ No JSON workflow files found in directory")
            return {'success': False, 'error': 'No workflow files found'}
        
        print(f"📊 Found {len(workflow_files)} workflow files")
        
        results = {
            'total_files': len(workflow_files),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'results': [],
            'summary': {}
        }
        
        # Process each file
        for filename in workflow_files:
            input_path = os.path.join(input_dir, filename)
            
            # Create backup if needed
            if create_backup and not output_dir:
                backup_path = input_path + '.backup'
                if not os.path.exists(backup_path):
                    with open(input_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            # Set output path
            if output_dir:
                output_path = os.path.join(output_dir, filename)
            else:
                output_path = input_path  # In-place update
            
            # Process the file
            result = self.process_single_workflow(input_path, output_path)
            results['results'].append(result)
            results['processed'] += 1
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            # Display progress
            print(f"Progress: {results['processed']}/{results['total_files']} "
                  f"(✅ {results['successful']} | ❌ {results['failed']})")
        
        # Create summary
        results['summary'] = self._create_processing_summary(results['results'])
        
        print(f"\n🏁 Processing completed!")
        print(f"📊 Total: {results['total_files']} | "
              f"✅ Success: {results['successful']} | "
              f"❌ Failed: {results['failed']}")
        
        return results
    
    def _display_workflow_analysis(self, workflow_id: str, metadata: Dict[str, Any], 
                                 workflow_data: Dict[str, Any]) -> None:
        """Display workflow analysis"""
        
        print(f"\n📈 Analysis Results for Workflow {workflow_id}:")
        print(f"─" * 50)
        
        print(f"🔢 Nodes Count: {metadata.get('nodes_count', 0)}")
        print(f"📱 Platforms: {', '.join(metadata.get('platforms', []))}")
        print(f"🔐 Credentials: {', '.join(metadata.get('credentials', []))}")
        print(f"📂 Categories: {', '.join(metadata.get('categories', []))}")
        print(f"🎯 Triggers: {', '.join(metadata.get('triggers', []))}")
        print(f"⚡ Actions: {', '.join(metadata.get('actions', []))}")
        print(f"📊 Difficulty: {metadata.get('difficulty', 'Unknown')}")
        
        # Display additional info if exists
        if 'title' in workflow_data:
            print(f"📝 Title: {workflow_data['title']}")
        if 'description' in workflow_data:
            print(f"📖 Description: {workflow_data['description']}")
        
        print(f"─" * 50)
    
    def _create_processing_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create processing summary"""
        
        successful_results = [r for r in results if r.get('success')]
        
        if not successful_results:
            return {'message': 'No successful processing results'}
        
        # Collect statistics
        all_platforms = []
        all_categories = []
        difficulties = []
        nodes_counts = []
        
        for result in successful_results:
            metadata = result.get('metadata', {})
            all_platforms.extend(metadata.get('platforms', []))
            all_categories.extend(metadata.get('categories', []))
            difficulties.append(metadata.get('difficulty', 'Unknown'))
            nodes_counts.append(metadata.get('nodes_count', 0))
        
        # Count
        from collections import Counter
        
        return {
            'workflows_processed': len(successful_results),
            'top_platforms': dict(Counter(all_platforms).most_common(10)),
            'top_categories': dict(Counter(all_categories).most_common()),
            'difficulty_distribution': dict(Counter(difficulties)),
            'average_nodes': sum(nodes_counts) / len(nodes_counts) if nodes_counts else 0,
            'max_nodes': max(nodes_counts) if nodes_counts else 0,
            'min_nodes': min(nodes_counts) if nodes_counts else 0
        }
    
    def analyze_workflow_content(self, workflow_file: str) -> Dict[str, Any]:
        """Detailed analysis of workflow content (without modifying the file)"""
        
        workflow_data = load_workflow_file(workflow_file)
        content = workflow_data.get('content', {})
        nodes = content.get('nodes', [])
        connections = content.get('connections', {})
        
        # Analyze nodes
        node_analysis = {}
        for node in nodes:
            node_type = node.get('type', '').replace('n8n-nodes-base.', '')
            metadata = self.mapper.get_node_metadata(node.get('type', ''))
            
            node_analysis[node.get('name', node_type)] = {
                'type': node_type,
                'category': metadata.get('category'),
                'service': metadata.get('service_name'),
                'parameters_count': len(node.get('parameters', {})),
                'position': node.get('position', [])
            }
        
        # Analyze connections
        connection_count = sum(len(conns) for conns in connections.values())
        
        return {
            'workflow_id': workflow_data.get('id'),
            'total_nodes': len(nodes),
            'total_connections': connection_count,
            'node_types': list(set(node.get('type', '').replace('n8n-nodes-base.', '') for node in nodes)),
            'node_analysis': node_analysis,
            'complexity_score': len(nodes) + connection_count + len(set(node.get('type', '') for node in nodes)),
            'metadata_generated': self.mapper.extract_workflow_metadata(workflow_data)
        }

def main():
    """Main function for command line execution"""
    
    parser = argparse.ArgumentParser(description='Process N8N Workflow JSON files')
    parser.add_argument('input', help='Input workflow file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-m', '--mapping', default='enhanced_n8n_mapping.json', 
                       help='Mapping file to use')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup files before processing')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze without modifying files')
    
    args = parser.parse_args()
    
    # Create processor
    processor = WorkflowProcessor(args.mapping)
    
    try:
        if os.path.isfile(args.input):
            # Process single file
            if args.analyze_only:
                analysis = processor.analyze_workflow_content(args.input)
                print(json.dumps(analysis, indent=2, ensure_ascii=False))
            else:
                result = processor.process_single_workflow(args.input, args.output)
                if not result['success']:
                    sys.exit(1)
        
        elif os.path.isdir(args.input):
            # Process directory
            if args.analyze_only:
                print("📊 Analysis mode for directories not implemented yet")
                sys.exit(1)
            else:
                results = processor.process_multiple_workflows(
                    args.input, args.output, args.backup
                )
                
                if results['failed'] > 0:
                    print(f"\n⚠️ {results['failed']} files failed to process")
                    sys.exit(1)
        
        else:
            print(f"❌ Error: {args.input} is not a valid file or directory")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 