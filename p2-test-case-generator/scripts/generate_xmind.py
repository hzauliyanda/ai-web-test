#!/usr/bin/env python3
"""
Generate XMind file from test cases markdown file.

Uses xmind-sdk to produce proper XMind 8 XML format that all XMind versions
can open correctly, including full hierarchy (children/subtopics).

Features:
- Priority marker icons (P0: red, P1: orange, P2: blue)
- Structured hierarchy: Root -> Module -> Priority -> Test Case -> Details
- Chinese and English markdown support

Usage:
    python generate_xmind.py test-cases.md
    python generate_xmind.py test-cases.md output.xmind
"""

import re
import sys
from pathlib import Path

import xmind
from xmind.core.markerref import MarkerId


PRIORITY_MARKERS = {
    'P0': MarkerId.priority1,
    'P1': MarkerId.priority2,
    'P2': MarkerId.priority3,
}

PRIORITY_ICONS = {
    'P0': '🔴',
    'P1': '🟠',
    'P2': '🔵',
}


def parse_markdown_to_xmind(md_content, output_path):
    """Parse markdown test cases and generate XMind file."""
    lines = md_content.split('\n')

    title = '测试用例'
    for line in lines[:10]:
        if line.startswith('# ') and not line.startswith('## '):
            title = line.replace('# ', '').strip()
            break

    wb = xmind.load(str(output_path))
    sheet = wb.getPrimarySheet()
    sheet.setTitle(title)
    root = sheet.getRootTopic()
    root.setTitle(title)

    current_module_topic = None
    current_priority_topic = None
    current_tc_topic = None
    current_section_topic = None
    current_section = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith('## '):
            module_name = stripped.replace('## ', '').strip()
            if module_name:
                topic = wb.createTopic()
                topic.setTitle(f'📦 {module_name}')
                root.addSubTopic(topic)
                current_module_topic = topic
                current_priority_topic = None
                current_tc_topic = None
                current_section_topic = None
                current_section = None

        elif stripped.startswith('### P') and current_module_topic:
            priority = stripped.replace('### ', '').split(' ')[0].strip()
            icon = PRIORITY_ICONS.get(priority, '⚪')
            topic = wb.createTopic()
            topic.setTitle(f'{icon} {priority}')
            if priority in PRIORITY_MARKERS:
                topic.addMarker(PRIORITY_MARKERS[priority])
            current_module_topic.addSubTopic(topic)
            current_priority_topic = topic
            current_tc_topic = None
            current_section_topic = None
            current_section = None

        elif stripped.startswith('#### TC-') and current_priority_topic:
            match = re.match(r'#### (TC-[\w-]+):\s*(.+)', stripped)
            if match:
                tc_id = match.group(1)
                tc_title = match.group(2).strip()
                topic = wb.createTopic()
                topic.setTitle(f'{tc_id}: {tc_title}')
                current_priority_topic.addSubTopic(topic)
                current_tc_topic = topic
                current_section_topic = None
                current_section = None

        elif current_tc_topic:
            if '优先级' in stripped or 'Priority' in stripped:
                priority_value = re.sub(r'\*\*优先级\*\*[：:]\s*', '', stripped)
                priority_value = re.sub(r'\*\*Priority\*\*[：:]\s*', '', priority_value)
                priority_value = priority_value.replace('**', '').strip()
                topic = wb.createTopic()
                topic.setTitle(f'⚡ {priority_value}')
                current_tc_topic.addSubTopic(topic)
                current_section = None

            elif '测试类型' in stripped or 'Test Type' in stripped:
                test_type = re.sub(r'\*\*测试类型\*\*[：:]\s*', '', stripped)
                test_type = re.sub(r'\*\*Test Type\*\*[：:]\s*', '', test_type)
                test_type = test_type.replace('**', '').strip()
                topic = wb.createTopic()
                topic.setTitle(f'🔧 {test_type}')
                current_tc_topic.addSubTopic(topic)
                current_section = None

            elif '描述' in stripped or 'Description' in stripped:
                desc = re.sub(r'\*\*描述\*\*[：:]\s*', '', stripped)
                desc = re.sub(r'\*\*Description\*\*[：:]\s*', '', desc)
                desc = desc.replace('**', '').strip()
                if desc:
                    topic = wb.createTopic()
                    topic.setTitle(f'📝 {desc}')
                    current_tc_topic.addSubTopic(topic)
                current_section = None

            elif '前置条件' in stripped or 'Prerequisites' in stripped:
                topic = wb.createTopic()
                topic.setTitle('✅ 前置条件')
                current_tc_topic.addSubTopic(topic)
                current_section_topic = topic
                current_section = 'prerequisites'

            elif '测试步骤' in stripped or 'Test Steps' in stripped:
                topic = wb.createTopic()
                topic.setTitle('📋 测试步骤')
                current_tc_topic.addSubTopic(topic)
                current_section_topic = topic
                current_section = 'steps'

            elif '预期结果' in stripped or 'Expected Result' in stripped:
                topic = wb.createTopic()
                topic.setTitle('🎯 预期结果')
                current_tc_topic.addSubTopic(topic)
                current_section_topic = topic
                current_section = 'result'

            elif '实现参考' in stripped or 'Implementation Reference' in stripped:
                impl = re.sub(r'\*\*实现参考\*\*[：:]\s*', '', stripped)
                impl = re.sub(r'\*\*Implementation Reference\*\*[：:]\s*', '', impl)
                impl = impl.replace('**', '').strip()
                topic = wb.createTopic()
                topic.setTitle('💻 实现参考')
                current_tc_topic.addSubTopic(topic)
                if impl:
                    impl_topic = wb.createTopic()
                    impl_topic.setTitle(impl)
                    topic.addSubTopic(impl_topic)
                current_section_topic = topic
                current_section = 'impl'

            elif stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped):
                if current_section_topic:
                    item_text = stripped.lstrip('- ')
                    number_match = re.match(r'^(\d+)\.\s', stripped)
                    if number_match:
                        item_text = re.sub(r'^\d+\.\s', '', stripped)
                    item_text = item_text.strip().strip('-').strip()

                    if item_text:
                        item_topic = wb.createTopic()
                        item_topic.setTitle(item_text)
                        current_section_topic.addSubTopic(item_topic)

    xmind.save(wb)
    return output_path


def count_test_cases(md_content):
    """Count modules, test cases, and priority distribution."""
    lines = md_content.split('\n')
    modules = 0
    total = 0
    p_counts = {'P0': 0, 'P1': 0, 'P2': 0}
    current_priority = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## '):
            modules += 1
            current_priority = None
        elif stripped.startswith('### P'):
            priority = stripped.replace('### ', '').split(' ')[0].strip()
            current_priority = priority
        elif stripped.startswith('#### TC-') and current_priority:
            total += 1
            if current_priority in p_counts:
                p_counts[current_priority] += 1

    return modules, total, p_counts


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("XMind Test Case Generator v3.0")
        print("=" * 60)
        print("\nUsage:")
        print("  python generate_xmind.py <markdown_file> [output_file]")
        print("\nExamples:")
        print("  python generate_xmind.py test-cases.md")
        print("  python generate_xmind.py test-cases.md output.xmind")
        print("\nFeatures:")
        print("  ✅ XMind 8 XML format (compatible with all versions)")
        print("  🔴 P0 priority marker (red)")
        print("  🟠 P1 priority marker (orange)")
        print("  🔵 P2 priority marker (blue)")
        print("  ✅ Full hierarchy with children/subtopics")
        print("=" * 60)
        sys.exit(1)

    md_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    md_path = Path(md_file)
    if not md_path.exists():
        print(f"❌ Error: File not found: {md_path}")
        sys.exit(1)

    DEFAULT_OUTPUT_DIR = Path.home() / 'AI-TEST' / 'TestCase'
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if output_file is None:
        output_path = DEFAULT_OUTPUT_DIR / md_path.with_suffix('.xmind').name
    else:
        output_path = Path(output_file)

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    print(f"📖 Reading: {md_path}")

    modules, total, p_counts = count_test_cases(md_content)

    print("\n" + "=" * 60)
    print("XMind Test Cases Summary")
    print("=" * 60)
    print(f"📦 Modules: {modules}")
    print(f"📝 Total Test Cases: {total}")
    print(f"\nPriority Distribution:")
    print(f"  🔴 P0 (Critical): {p_counts['P0']}")
    print(f"  🟠 P1 (Important): {p_counts['P1']}")
    print(f"  🔵 P2 (Normal): {p_counts['P2']}")
    print("=" * 60)

    result = parse_markdown_to_xmind(md_content, str(output_path))

    import os
    print(f"\n✅ Successfully created XMind file: {output_path}")
    print(f"   File size: {os.path.getsize(output_path)} bytes")
    print("\n💡 Tips:")
    print("   - Uses XMind 8 XML format for maximum compatibility")
    print("   - All hierarchy levels are preserved as subtopics")
    print("   - Priority markers displayed as icons in XMind")
    print("   - Open with XMind 8+ or XMind 2020+")


if __name__ == '__main__':
    main()