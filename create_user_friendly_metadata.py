#!/usr/bin/env python3
"""
Create User-Friendly Metadata for N8N Workflows
Extracts comprehensive metadata from nodes-base and workflows to create user-friendly structure
"""

import json
import os
import re
from typing import Dict, List, Set, Any, Optional
from pathlib import Path
import argparse
from collections import defaultdict, Counter

class N8NMetadataExtractor:
    def __init__(self):
        self.nodes_metadata = {}
        self.category_mapping = {}
        self.action_mapping = {}
        self.trigger_mapping = {}
        self.use_case_mapping = {}
        self.service_mapping = {}
        
    def extract_node_metadata_from_ts_file(self, file_path: str) -> Dict[str, Any]:
        """חילוץ מטאדאטה מפורטת מקובץ .node.ts"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {
                'display_name': '',
                'description': '',
                'subtitle': '',
                'group': [],
                'use_cases': [],
                'actions': [],
                'triggers': [],
                'difficulty': 'Beginner',
                'setup_requirements': []
            }
            
            # חילוץ displayName
            display_match = re.search(r'displayName:\s*[\'"]([^\'"]+)[\'"]', content)
            if display_match:
                metadata['display_name'] = display_match.group(1)
            
            # חילוץ description
            desc_match = re.search(r'description:\s*[\'"]([^\'"]+)[\'"]', content)
            if desc_match:
                metadata['description'] = desc_match.group(1)
            
            # חילוץ subtitle
            subtitle_match = re.search(r'subtitle:\s*[\'"]([^\'"]+)[\'"]', content)
            if subtitle_match:
                metadata['subtitle'] = subtitle_match.group(1)
            
            # חילוץ group
            group_match = re.search(r'group:\s*\[(.*?)\]', content, re.DOTALL)
            if group_match:
                groups = re.findall(r'[\'"]([^\'"]+)[\'"]', group_match.group(1))
                metadata['group'] = groups
            
            # חילוץ properties כדי להבין actions
            properties_match = re.search(r'properties:\s*\[(.*?)\]', content, re.DOTALL)
            if properties_match:
                props = properties_match.group(1)
                # חיפוש operations ו-resources
                operation_matches = re.findall(r'operation.*?options.*?\[(.*?)\]', props, re.DOTALL)
                for operation_match in operation_matches:
                    actions = re.findall(r'name:\s*[\'"]([^\'"]+)[\'"]', operation_match)
                    metadata['actions'].extend(actions)
                
                resource_matches = re.findall(r'resource.*?options.*?\[(.*?)\]', props, re.DOTALL)
                for resource_match in resource_matches:
                    resources = re.findall(r'name:\s*[\'"]([^\'"]+)[\'"]', resource_match)
                    metadata['actions'].extend(resources)
            
            # קביעת difficulty בהתבסס על מורכבות
            if 'webhook' in content.lower() or 'trigger' in metadata['display_name'].lower():
                metadata['difficulty'] = 'Intermediate'
            if 'api' in content.lower() and 'authentication' in content.lower():
                metadata['difficulty'] = 'Advanced'
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting from {file_path}: {e}")
            return {}
    
    def extract_node_metadata_from_json(self, file_path: str) -> Dict[str, Any]:
        """חילוץ מטאדאטה מקובץ .node.json"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = {
                'categories': data.get('categories', []),
                'alias': data.get('alias', []),
                'use_cases': []
            }
            
            # חילוץ use cases מ-resources.generic
            if 'resources' in data and 'generic' in data['resources']:
                for resource in data['resources']['generic']:
                    if 'label' in resource:
                        metadata['use_cases'].append(resource['label'])
            
            return metadata
            
        except Exception as e:
            print(f"Error extracting from {file_path}: {e}")
            return {}
    
    def scan_nodes_base_directory(self, nodes_base_path: str) -> Dict[str, Dict[str, Any]]:
        """סריקה מלאה של תיקיית nodes-base"""
        nodes_metadata = {}
        
        for root, dirs, files in os.walk(nodes_base_path):
            for file in files:
                if file.endswith('.node.ts'):
                    file_path = os.path.join(root, file)
                    node_name = file.replace('.node.ts', '')
                    
                    # חילוץ מטאדאטה מקובץ TS
                    ts_metadata = self.extract_node_metadata_from_ts_file(file_path)
                    
                    # חיפוש קובץ JSON מתאים
                    json_file = file.replace('.node.ts', '.node.json')
                    json_path = os.path.join(root, json_file)
                    
                    json_metadata = {}
                    if os.path.exists(json_path):
                        json_metadata = self.extract_node_metadata_from_json(json_path)
                    
                    # איחוד המטאדאטה
                    combined_metadata = {**ts_metadata, **json_metadata}
                    
                    # יצירת מפתח לפי n8n naming convention
                    if combined_metadata and combined_metadata.get('display_name'):
                        # חילוץ שם ה-node type מהקובץ
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # חיפוש name field בתוך הclass
                        name_match = re.search(r'name:\s*[\'"]([^\'"]+)[\'"]', content)
                        if name_match:
                            node_type = name_match.group(1)
                            # הוספה עם הפורמט המלא
                            nodes_metadata[f"n8n-nodes-base.{node_type}"] = combined_metadata
                            # הוספה גם בלי הprefix למקרה הצורך
                            nodes_metadata[node_type] = combined_metadata
                        else:
                            nodes_metadata[node_name] = combined_metadata
        
        return nodes_metadata
    
    def create_user_friendly_mapping(self, nodes_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """יצירת מיפוי user-friendly"""
        
        # מיפוי services (שמות ידידותיים)
        service_mapping = {}
        categories_mapping = defaultdict(list)
        triggers_mapping = defaultdict(list)
        actions_mapping = defaultdict(list)
        difficulty_mapping = defaultdict(list)
        use_cases_mapping = defaultdict(list)
        
        for node_name, metadata in nodes_metadata.items():
            display_name = metadata.get('display_name', node_name)
            
            # חילוץ שם השירות
            service_name = self.extract_service_name(display_name)
            service_mapping[node_name] = service_name
            
            # מיפוי קטגוריות
            categories = metadata.get('categories', [])
            for category in categories:
                categories_mapping[category].append(service_name)
            
            # מיפוי triggers
            if 'trigger' in metadata.get('group', []):
                triggers_mapping[service_name].append(f"New {service_name} Event")
            
            # מיפוי actions
            actions = metadata.get('actions', [])
            for action in actions:
                actions_mapping[service_name].append(action)
            
            # מיפוי difficulty
            difficulty = metadata.get('difficulty', 'Beginner')
            difficulty_mapping[difficulty].append(service_name)
            
            # מיפוי use cases
            use_cases = metadata.get('use_cases', [])
            for use_case in use_cases:
                use_cases_mapping[service_name].append(use_case)
        
        return {
            'service_mapping': dict(service_mapping),
            'categories_mapping': dict(categories_mapping),
            'triggers_mapping': dict(triggers_mapping),
            'actions_mapping': dict(actions_mapping),
            'difficulty_mapping': dict(difficulty_mapping),
            'use_cases_mapping': dict(use_cases_mapping)
        }
    
    def extract_service_name(self, display_name: str) -> str:
        """חילוץ שם השירות מהשם המלא"""
        # הסרת מילים כמו "Trigger", "Node", etc.
        service_name = re.sub(r'\s*(Trigger|Node|API|OAuth2?)?\s*$', '', display_name, flags=re.IGNORECASE)
        
        # טיפול במקרים מיוחדים
        special_cases = {
            'Google Sheets': 'Google Sheets',
            'Google Drive': 'Google Drive',
            'Google Calendar': 'Google Calendar',
            'TypeForm': 'Typeform',
            'Active Campaign': 'ActiveCampaign'
        }
        
        for pattern, replacement in special_cases.items():
            if pattern.lower() in service_name.lower():
                return replacement
        
        return service_name.strip()
    
    def analyze_workflow(self, workflow_data: Dict[str, Any], user_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """ניתוח workflow יחיד וחילוץ metadata user-friendly"""
        
        nodes = workflow_data.get('content', {}).get('nodes', [])
        if not nodes:
            return {}
        
        # חילוץ services בשימוש
        services = set()
        triggers = set()
        actions = set()
        categories = set()
        difficulty_scores = []
        setup_requirements = set()
        
        for node in nodes:
            node_type = node.get('type', '')
            node_name = node.get('name', '')
            
            # מיפוי לשירות - נבדוק גם עם וגם בלי הprefix
            service = user_mapping['service_mapping'].get(node_type, '')
            if not service:
                # נסה בלי הprefix
                clean_type = node_type.replace('n8n-nodes-base.', '')
                service = user_mapping['service_mapping'].get(clean_type, '')
            
            if service and service.strip():
                services.add(service)
            
            # זיהוי triggers
            if 'trigger' in node_type.lower() or 'trigger' in node_name.lower():
                if service and service.strip():
                    triggers.add(f"New {service} Event")
                else:
                    triggers.add("Workflow Trigger")
            
            # זיהוי actions
            node_params = node.get('parameters', {})
            operation = node_params.get('operation', '')
            resource = node_params.get('resource', '')
            
            if operation:
                actions.add(operation.title())
            if resource:
                actions.add(f"Manage {resource}")
                
            # זיהוי core actions
            if 'set' in node_type.lower():
                actions.add("Set Data")
            elif 'if' in node_type.lower():
                actions.add("Filter Data")
            elif 'function' in node_type.lower():
                actions.add("Execute Function")
            
            # זיהוי credentials נדרשים
            credentials = node.get('credentials', {})
            for cred_type in credentials.keys():
                if 'OAuth2' in cred_type:
                    if service and service.strip():
                        setup_requirements.add(f"{service} Account")
                elif 'Api' in cred_type:
                    if service and service.strip():
                        setup_requirements.add(f"{service} API Key")
        
        # קביעת categories בהתבסס על services
        for service in services:
            for category, category_services in user_mapping['categories_mapping'].items():
                if service in category_services:
                    categories.add(category)
        
        # קביעת difficulty
        difficulty = self.calculate_workflow_difficulty(nodes, len(services))
        
        return {
            'services': sorted(list(services)),
            'categories': sorted(list(categories)),
            'difficulty': difficulty,
            'triggers': sorted(list(triggers)),
            'actions': sorted(list(actions)),
            'setup_requirements': sorted(list(setup_requirements)),
            'workflow_complexity': len(nodes),
            'external_integrations_count': len(services)
        }
    
    def calculate_workflow_difficulty(self, nodes: List[Dict], services_count: int) -> str:
        """חישוב רמת קושי של workflow"""
        node_count = len(nodes)
        
        # בדיקת סוגי nodes מורכבים
        complex_nodes = 0
        for node in nodes:
            node_type = node.get('type', '').lower()
            if any(keyword in node_type for keyword in ['webhook', 'api', 'code', 'function']):
                complex_nodes += 1
        
        # חישוב ציון
        complexity_score = 0
        complexity_score += min(node_count // 3, 3)  # 0-3 בהתבסס על מספר nodes
        complexity_score += min(services_count // 2, 2)  # 0-2 בהתבסס על מספר שירותים
        complexity_score += complex_nodes  # +1 לכל node מורכב
        
        if complexity_score <= 2:
            return 'Beginner'
        elif complexity_score <= 5:
            return 'Intermediate'
        else:
            return 'Advanced'
    
    def update_all_workflows(self, workflows_dir: str, user_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """עדכון כל ה-workflows עם metadata user-friendly"""
        
        results = {
            'updated_count': 0,
            'services_added': Counter(),
            'categories_added': Counter(),
            'difficulties': Counter(),
            'errors': []
        }
        
        # עבור על כל קבצי ה-workflows
        for filename in os.listdir(workflows_dir):
            if not filename.endswith('.json'):
                continue
                
            workflow_file = os.path.join(workflows_dir, filename)
            
            try:
                # קריאת workflow
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    workflow_data = json.load(f)
                
                # ניתוח והוספת metadata
                new_metadata = self.analyze_workflow(workflow_data, user_mapping)
                
                if new_metadata:
                    # עדכון workflow
                    workflow_data.update(new_metadata)
                    
                    # שמירת workflow
                    with open(workflow_file, 'w', encoding='utf-8') as f:
                        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                    
                    # עדכון סטטיסטיקות
                    results['updated_count'] += 1
                    results['services_added'].update(new_metadata.get('services', []))
                    results['categories_added'].update(new_metadata.get('categories', []))
                    results['difficulties'][new_metadata.get('difficulty', 'Unknown')] += 1
                
            except Exception as e:
                results['errors'].append(f"Error processing {filename}: {str(e)}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Extract user-friendly metadata from N8N workflows')
    parser.add_argument('--nodes-base-path', default='nodes-base', help='Path to nodes-base directory')
    parser.add_argument('--workflows-dir', default='workflows', help='Path to workflows directory')
    parser.add_argument('--output-mapping', default='user_friendly_mapping.json', help='Output mapping file')
    parser.add_argument('--create-mapping-only', action='store_true', help='Only create mapping, don\'t update workflows')
    parser.add_argument('--sample-workflow', help='Test with single workflow file')
    
    args = parser.parse_args()
    
    extractor = N8NMetadataExtractor()
    
    print("🔍 Scanning nodes-base directory...")
    nodes_metadata = extractor.scan_nodes_base_directory(args.nodes_base_path)
    print(f"✅ Found metadata for {len(nodes_metadata)} nodes")
    
    print("🛠️ Creating user-friendly mapping...")
    user_mapping = extractor.create_user_friendly_mapping(nodes_metadata)
    print(f"✅ Created mapping for {len(user_mapping['service_mapping'])} services")
    
    # שמירת mapping
    with open(args.output_mapping, 'w', encoding='utf-8') as f:
        json.dump(user_mapping, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved mapping to {args.output_mapping}")
    
    # הדפסת סטטיסטיקות
    print("\n📊 Mapping Statistics:")
    print(f"Services: {len(user_mapping['service_mapping'])}")
    print(f"Categories: {len(user_mapping['categories_mapping'])}")
    print(f"Triggers: {sum(len(triggers) for triggers in user_mapping['triggers_mapping'].values())}")
    print(f"Actions: {sum(len(actions) for actions in user_mapping['actions_mapping'].values())}")
    
    if args.sample_workflow:
        print(f"\n🧪 Testing with sample workflow: {args.sample_workflow}")
        try:
            with open(args.sample_workflow, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
            
            sample_result = extractor.analyze_workflow(sample_data, user_mapping)
            print("✅ Sample analysis result:")
            print(json.dumps(sample_result, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"❌ Error testing sample: {e}")
    
    if not args.create_mapping_only:
        print("\n🚀 Updating all workflows...")
        results = extractor.update_all_workflows(args.workflows_dir, user_mapping)
        
        print(f"\n✅ Update completed!")
        print(f"Updated workflows: {results['updated_count']}")
        print(f"Errors: {len(results['errors'])}")
        
        print(f"\n📈 Top services:")
        for service, count in results['services_added'].most_common(10):
            print(f"  {service}: {count}")
        
        print(f"\n📂 Categories distribution:")
        for category, count in results['categories_added'].most_common():
            print(f"  {category}: {count}")
        
        print(f"\n🎯 Difficulty distribution:")
        for difficulty, count in results['difficulties'].most_common():
            print(f"  {difficulty}: {count}")
        
        if results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"  {error}")

if __name__ == "__main__":
    main() 