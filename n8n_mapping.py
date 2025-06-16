#!/usr/bin/env python3
"""
N8N Node Mapping System
Central mapping system for all N8N node types

Contains:
- Mapping of all node types to metadata
- Categories and definitions
- Services and integrations
- Helper functions for mapping

Created on 12/20/2024 by Itamar Zand
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class N8NNodeMapper:
    """Central class for all N8N mapping operations"""
    
    def __init__(self, mapping_file: str = "enhanced_n8n_mapping.json"):
        """Initialize with the latest mapping file"""
        self.mapping_file = mapping_file
        self.mapping_data = self.load_mapping()
        
    def load_mapping(self) -> Dict[str, Any]:
        """Load mapping data from file"""
        if os.path.exists(self.mapping_file):
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"❌ Mapping file not found: {self.mapping_file}")
            return {"nodes_metadata": {}}
    
    def get_node_metadata(self, node_type: str) -> Dict[str, Any]:
        """Get metadata for a specific node"""
        # Clean node name (remove prefix)
        clean_node_type = node_type.replace('n8n-nodes-base.', '')
        
        return self.mapping_data.get('nodes_metadata', {}).get(clean_node_type, {
            "display_name": clean_node_type,
            "description": f"Node type: {clean_node_type}",
            "group": ["transform"],
            "category": "Other",
            "service_name": clean_node_type,
            "difficulty": "Unknown",
            "keywords": []
        })
    
    def get_service_name(self, node_type: str) -> str:
        """Get service name for a node"""
        metadata = self.get_node_metadata(node_type)
        return metadata.get('service_name', node_type.replace('n8n-nodes-base.', ''))
    
    def get_category(self, node_type: str) -> str:
        """Get category for a node"""
        metadata = self.get_node_metadata(node_type)
        return metadata.get('category', 'Other')
    
    def get_platforms_from_nodes(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Extract list of platforms from nodes list"""
        platforms = set()
        
        for node in nodes:
            node_type = node.get('type', '')
            if node_type:
                service_name = self.get_service_name(node_type)
                # Add only if not a core node
                if not self._is_core_node(node_type):
                    platforms.add(service_name)
        
        return sorted(list(platforms))
    
    def get_categories_from_nodes(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Extract list of categories from nodes list"""
        categories = set()
        
        for node in nodes:
            node_type = node.get('type', '')
            if node_type:
                category = self.get_category(node_type)
                categories.add(category)
        
        return sorted(list(categories))
    
    def get_credentials_from_nodes(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Extract list of required credentials from nodes list"""
        credentials = set()
        
        for node in nodes:
            node_type = node.get('type', '')
            if node_type:
                metadata = self.get_node_metadata(node_type)
                # Check if node requires credentials
                if self._requires_credentials(node_type, metadata):
                    service_name = self.get_service_name(node_type)
                    credentials.add(service_name)
        
        return sorted(list(credentials))
    
    def _is_core_node(self, node_type: str) -> bool:
        """Check if this is a core node (not external service)"""
        core_nodes = {
            'Set', 'If', 'SplitInBatches', 'Item Lists', 'Merge', 'Function',
            'FunctionItem', 'Code', 'DateTime', 'Wait', 'Stop and Error',
            'NoOp', 'Webhook', 'Schedule Trigger', 'Manual Trigger',
            'Email Trigger (IMAP)', 'HTTP Request', 'Execute Command',
            'Read/Write Files from Disk', 'Spreadsheet File'
        }
        
        clean_type = node_type.replace('n8n-nodes-base.', '')
        return clean_type in core_nodes
    
    def _requires_credentials(self, node_type: str, metadata: Dict[str, Any]) -> bool:
        """Check if the node requires credentials"""
        # Most external nodes require credentials
        if self._is_core_node(node_type):
            return False
        
        # Certain nodes don't require credentials
        no_credentials_nodes = {
            'HTML Extract', 'RSS Feed Read', 'XML', 'GraphQL',
            'Wait', 'DateTime', 'Code', 'Function'
        }
        
        clean_type = node_type.replace('n8n-nodes-base.', '')
        return clean_type not in no_credentials_nodes
    
    def extract_workflow_metadata(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract complete workflow metadata"""
        content = workflow_data.get('content', {})
        nodes = content.get('nodes', [])
        
        # Extract all data
        platforms = self.get_platforms_from_nodes(nodes)
        categories = self.get_categories_from_nodes(nodes)
        credentials = self.get_credentials_from_nodes(nodes)
        
        # Count nodes
        nodes_count = len(nodes)
        
        # Identify triggers
        triggers = self._detect_triggers(nodes)
        
        # Identify actions
        actions = self._detect_actions(nodes)
        
        # Assess difficulty
        difficulty = self._assess_difficulty(nodes, platforms)
        
        return {
            'platforms': platforms,
            'categories': categories,
            'credentials': credentials,
            'nodes_count': nodes_count,
            'triggers': triggers,
            'actions': actions,
            'difficulty': difficulty
        }
    
    def _detect_triggers(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Identify trigger types in workflow"""
        triggers = set()
        
        trigger_mapping = {
            'Webhook': 'Webhook',
            'Schedule Trigger': 'Schedule',
            'Manual Trigger': 'Manual',
            'Email Trigger (IMAP)': 'Email',
            'File Trigger': 'File Changes'
        }
        
        for node in nodes:
            node_type = node.get('type', '').replace('n8n-nodes-base.', '')
            if node_type in trigger_mapping:
                triggers.add(trigger_mapping[node_type])
            elif 'Trigger' in node_type:
                triggers.add('Webhook')  # Most triggers are webhooks
        
        return sorted(list(triggers))
    
    def _detect_actions(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Identify action types in workflow"""
        actions = set()
        
        action_keywords = {
            'create': 'Create',
            'send': 'Send',
            'update': 'Update',
            'delete': 'Delete',
            'get': 'Read',
            'list': 'List',
            'search': 'Search',
            'sync': 'Sync'
        }
        
        for node in nodes:
            node_name = node.get('name', '').lower()
            for keyword, action in action_keywords.items():
                if keyword in node_name:
                    actions.add(action)
        
        return sorted(list(actions))
    
    def _assess_difficulty(self, nodes: List[Dict[str, Any]], platforms: List[str]) -> str:
        """Assess workflow difficulty level"""
        nodes_count = len(nodes)
        platforms_count = len(platforms)
        
        # Check for complex node types
        complex_nodes = {
            'Function', 'FunctionItem', 'Code', 'SplitInBatches',
            'Item Lists', 'HTTP Request'
        }
        
        has_complex_nodes = any(
            node.get('type', '').replace('n8n-nodes-base.', '') in complex_nodes
            for node in nodes
        )
        
        # Assess based on quantity and complexity
        if nodes_count <= 3 and platforms_count <= 2 and not has_complex_nodes:
            return "Beginner"
        elif nodes_count <= 8 and platforms_count <= 4:
            return "Intermediate"
        else:
            return "Advanced"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the mapping"""
        nodes_data = self.mapping_data.get('nodes_metadata', {})
        
        categories = {}
        services = set()
        
        for node_data in nodes_data.values():
            category = node_data.get('category', 'Other')
            categories[category] = categories.get(category, 0) + 1
            services.add(node_data.get('service_name', ''))
        
        return {
            'total_nodes': len(nodes_data),
            'total_services': len(services),
            'categories_breakdown': categories,
            'mapping_file': self.mapping_file
        }

# Helper functions outside the class
def load_workflow_file(file_path: str) -> Dict[str, Any]:
    """Load workflow file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_workflow_file(file_path: str, workflow_data: Dict[str, Any]) -> None:
    """Save workflow file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f, indent=2, ensure_ascii=False)

def process_all_workflows(workflows_dir: str, mapper: N8NNodeMapper) -> Dict[str, Any]:
    """Process all workflows in directory"""
    results = {
        'processed': 0,
        'updated': 0,
        'errors': 0,
        'stats': {}
    }
    
    workflow_files = [f for f in os.listdir(workflows_dir) if f.endswith('.json')]
    
    for filename in workflow_files:
        try:
            file_path = os.path.join(workflows_dir, filename)
            workflow_data = load_workflow_file(file_path)
            
            # Extract metadata
            metadata = mapper.extract_workflow_metadata(workflow_data)
            
            # Update workflow
            workflow_data.update(metadata)
            
            # Save back
            save_workflow_file(file_path, workflow_data)
            
            results['updated'] += 1
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            results['errors'] += 1
        
        results['processed'] += 1
    
    return results

if __name__ == "__main__":
    # Usage example
    mapper = N8NNodeMapper()
    print("🔧 N8N Node Mapper initialized")
    print(f"📊 Stats: {mapper.get_stats()}") 