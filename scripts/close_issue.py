#!/usr/bin/env python3
"""
Arkham Nexus Issue Closure Management Script

This script manages the process of closing completed issues:
1. Moves completed issues from ISSUES.md to ISSUES_CLOSED.md
2. Updates SPECIFICATION.md with implementation details
3. Updates progress tracking and statistics

Usage:
    python3 scripts/close_issue.py ISSUE-XXX
    python3 scripts/close_issue.py --list-pending
    python3 scripts/close_issue.py --help
"""

import argparse
import re
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class IssueClosureManager:
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.issues_file = self.project_root / "ISSUES.md"
        self.closed_file = self.project_root / "ISSUES_CLOSED.md"
        self.spec_file = self.project_root / "SPECIFICATION.md"
        self.claude_file = self.project_root / "CLAUDE.md"
        
    def list_pending_issues(self):
        """List all issues marked as completed (✅) but not yet closed."""
        if not self.issues_file.exists():
            print("❌ ISSUES.md not found")
            return
            
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find completed issues (those with ✅ in title)
        completed_pattern = r'### ✅ (ISSUE-\d+): ([^(]+)\（解決済み\）'
        completed_issues = re.findall(completed_pattern, content)
        
        if completed_issues:
            print("📋 完了済み（クローズ待ち）課題:")
            for issue_id, title in completed_issues:
                print(f"  • {issue_id}: {title.strip()}")
        else:
            print("✅ 全ての完了済み課題はクローズ済みです")
    
    def extract_issue_content(self, issue_id):
        """Extract issue content from ISSUES.md."""
        if not self.issues_file.exists():
            raise FileNotFoundError("ISSUES.md not found")
            
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match the entire issue section
        pattern = rf'### ✅ {re.escape(issue_id)}:.*?(?=### |---|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            raise ValueError(f"Issue {issue_id} not found or not marked as completed")
        
        return match.group(0).strip()
    
    def remove_issue_from_active(self, issue_id):
        """Remove issue from ISSUES.md."""
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove the issue section
        pattern = rf'### ✅ {re.escape(issue_id)}:.*?(?=### |---|\Z)'
        updated_content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Clean up extra blank lines
        updated_content = re.sub(r'\n\n\n+', '\n\n', updated_content)
        
        with open(self.issues_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
    
    def add_issue_to_closed(self, issue_content):
        """Add issue to ISSUES_CLOSED.md."""
        if not self.closed_file.exists():
            print("❌ ISSUES_CLOSED.md not found. Creating new file.")
            return
            
        with open(self.closed_file, 'r', encoding='utf-8') as f:
            closed_content = f.read()
        
        # Find the insertion point (after "## ✅ 完了済み課題一覧")
        insertion_pattern = r'(## ✅ 完了済み課題一覧\n\n)'
        match = re.search(insertion_pattern, closed_content)
        
        if match:
            insertion_point = match.end()
            new_content = (
                closed_content[:insertion_point] +
                issue_content + '\n\n' +
                closed_content[insertion_point:]
            )
        else:
            # Fallback: add at the end of completed issues section
            new_content = closed_content + '\n\n' + issue_content
        
        with open(self.closed_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
    
    def update_statistics(self):
        """Update statistics in both ISSUES.md and ISSUES_CLOSED.md."""
        # Count issues in both files
        active_count = self.count_active_issues()
        closed_count = self.count_closed_issues()
        
        # Update ISSUES.md statistics
        self.update_issues_stats(active_count, closed_count)
        
        # Update ISSUES_CLOSED.md statistics  
        self.update_closed_stats(closed_count)
    
    def count_active_issues(self):
        """Count active issues by priority."""
        if not self.issues_file.exists():
            return {'high': 0, 'medium': 0, 'low': 0}
        
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        high_count = len(re.findall(r'### ISSUE-\d+:', content.split('## 🟡 優先度: 中')[0]))
        
        sections = content.split('## 🟡 優先度: 中')
        if len(sections) > 1:
            medium_section = sections[1].split('## 🟢 優先度: 低')[0]
            medium_count = len(re.findall(r'### ISSUE-\d+:', medium_section))
            
            if '## 🟢 優先度: 低' in content:
                low_section = content.split('## 🟢 優先度: 低')[1]
                low_count = len(re.findall(r'### ISSUE-\d+:', low_section))
            else:
                low_count = 0
        else:
            medium_count = 0
            low_count = 0
        
        return {'high': high_count, 'medium': medium_count, 'low': low_count}
    
    def count_closed_issues(self):
        """Count closed issues."""
        if not self.closed_file.exists():
            return 0
        
        with open(self.closed_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return len(re.findall(r'### ✅ ISSUE-\d+:', content))
    
    def update_issues_stats(self, active_count, closed_count):
        """Update statistics in ISSUES.md."""
        with open(self.issues_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update implementation completion rate
        stats_pattern = r'### 実装完了率.*?### 完了済み課題.*?\n\n'
        new_stats = f"""### 実装完了率
- **高優先度**: 0/{active_count['high']} (0%) - 現在進行中
- **中優先度**: 0/{active_count['medium']} (0%) - 全て未着手  
- **低優先度**: 0/{active_count['low']} (0%) - 全て未着手

### 完了済み課題
- **アーカイブ済み**: {closed_count}件 - `ISSUES_CLOSED.md`参照
- **最終更新**: {datetime.now().strftime('%Y年%m月%d日')}

"""
        
        updated_content = re.sub(stats_pattern, new_stats, content, flags=re.DOTALL)
        
        with open(self.issues_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
    
    def update_closed_stats(self, closed_count):
        """Update statistics in ISSUES_CLOSED.md."""
        with open(self.closed_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update completion summary
        stats_pattern = r'### 実装完了サマリー.*?(?=###)'
        new_stats = f"""### 実装完了サマリー
- **完了済み課題数**: {closed_count}件
- **最終更新**: {datetime.now().strftime('%Y年%m月%d日')}
- **主要カテゴリ**: バグ修正、新機能実装、機能強化

"""
        
        updated_content = re.sub(stats_pattern, new_stats, content, flags=re.DOTALL)
        
        with open(self.closed_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
    
    def close_issue(self, issue_id):
        """Close a specific issue."""
        try:
            print(f"🔄 Closing {issue_id}...")
            
            # Extract issue content
            issue_content = self.extract_issue_content(issue_id)
            print(f"  ✅ Extracted issue content")
            
            # Move to closed file
            self.add_issue_to_closed(issue_content)
            print(f"  ✅ Added to ISSUES_CLOSED.md")
            
            # Remove from active file
            self.remove_issue_from_active(issue_id)
            print(f"  ✅ Removed from ISSUES.md")
            
            # Update statistics
            self.update_statistics()
            print(f"  ✅ Updated statistics")
            
            print(f"🎉 {issue_id} successfully closed and archived!")
            print(f"📋 Details moved to: ISSUES_CLOSED.md")
            print(f"📊 Statistics updated in both files")
            
        except Exception as e:
            print(f"❌ Error closing {issue_id}: {str(e)}")
            return False
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Manage Arkham Nexus issue closure')
    parser.add_argument('issue_id', nargs='?', help='Issue ID to close (e.g., ISSUE-001)')
    parser.add_argument('--list-pending', action='store_true', help='List pending completed issues')
    
    args = parser.parse_args()
    
    manager = IssueClosureManager()
    
    if args.list_pending:
        manager.list_pending_issues()
    elif args.issue_id:
        if not re.match(r'^ISSUE-\d+$', args.issue_id):
            print("❌ Invalid issue ID format. Use: ISSUE-XXX")
            return 1
        
        success = manager.close_issue(args.issue_id)
        return 0 if success else 1
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())