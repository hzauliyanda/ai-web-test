#!/usr/bin/env python3
"""
Generate XMind Zen format file from test cases markdown file.

XMind Zen (XMind 2020+) uses JSON-based content format instead of XML.
The .xmind file is a ZIP containing content.json and metadata.json.

This format provides better compatibility with XMind 2020+, XMind Zen,
and XMind for iOS/Android.

Usage:
    python generate_xmind_zen.py test-cases.md
    python generate_xmind_zen.py test-cases.md output.xmind
"""

import json
import re
import sys
import uuid
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PRIORITY_ICONS = {
    'P0': '🔴',
    'P1': '🟠',
    'P2': '🔵',
}

PRIORITY_MARKERS = {
    'P0': 'priority-1',
    'P1': 'priority-2',
    'P2': 'priority-3',
}


def _gen_id():
    return uuid.uuid4().hex[:26]


def _make_topic(title, markers=None):
    topic = {
        'id': _gen_id(),
        'class': 'topic',
        'title': title,
        'children': {'attached': []},
    }
    if markers:
        topic['markers'] = markers
    return topic


def _add_child(parent_topic, child_topic):
    parent_topic['children']['attached'].append(child_topic)


def count_test_cases(md_content):
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


def build_zen_from_md(md_content):
    lines = md_content.split('\n')

    title = '测试用例'
    for line in lines[:10]:
        if line.startswith('# ') and not line.startswith('## '):
            title = line.replace('# ', '').strip()
            break

    root_topic = _make_topic(title)

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
                current_module_topic = _make_topic(f'📦 {module_name}')
                _add_child(root_topic, current_module_topic)
                current_priority_topic = None
                current_tc_topic = None
                current_section_topic = None
                current_section = None

        elif stripped.startswith('### P') and current_module_topic is not None:
            priority = stripped.replace('### ', '').split(' ')[0].strip()
            icon = PRIORITY_ICONS.get(priority, '⚪')
            marker_id = PRIORITY_MARKERS.get(priority)
            markers = [{'markerId': marker_id, 'id': _gen_id()}] if marker_id else None
            current_priority_topic = _make_topic(f'{icon} {priority}', markers=markers)
            _add_child(current_module_topic, current_priority_topic)
            current_tc_topic = None
            current_section_topic = None
            current_section = None

        elif stripped.startswith('#### TC-') and current_priority_topic is not None:
            match = re.match(r'#### (TC-[\w-]+):\s*(.+)', stripped)
            if match:
                tc_id = match.group(1)
                tc_title = match.group(2).strip()
                current_tc_topic = _make_topic(f'{tc_id}: {tc_title}')
                _add_child(current_priority_topic, current_tc_topic)
                current_section_topic = None
                current_section = None

        elif current_tc_topic is not None:
            if '优先级' in stripped or 'Priority' in stripped:
                priority_value = re.sub(r'\*\*优先级\*\*[：:]\s*', '', stripped)
                priority_value = re.sub(r'\*\*Priority\*\*[：:]\s*', '', priority_value)
                priority_value = priority_value.replace('**', '').strip()
                section_topic = _make_topic(f'⚡ {priority_value}')
                _add_child(current_tc_topic, section_topic)
                current_section_topic = None
                current_section = None

            elif '测试类型' in stripped or 'Test Type' in stripped:
                test_type = re.sub(r'\*\*测试类型\*\*[：:]\s*', '', stripped)
                test_type = re.sub(r'\*\*Test Type\*\*[：:]\s*', '', test_type)
                test_type = test_type.replace('**', '').strip()
                section_topic = _make_topic(f'🔧 {test_type}')
                _add_child(current_tc_topic, section_topic)
                current_section_topic = None
                current_section = None

            elif '描述' in stripped or 'Description' in stripped:
                desc = re.sub(r'\*\*描述\*\*[：:]\s*', '', stripped)
                desc = re.sub(r'\*\*Description\*\*[：:]\s*', '', desc)
                desc = desc.replace('**', '').strip()
                if desc:
                    section_topic = _make_topic(f'📝 {desc}')
                    _add_child(current_tc_topic, section_topic)
                current_section_topic = None
                current_section = None

            elif '前置条件' in stripped or 'Prerequisites' in stripped:
                section_topic = _make_topic('✅ 前置条件')
                _add_child(current_tc_topic, section_topic)
                current_section_topic = section_topic
                current_section = 'prerequisites'

            elif '测试步骤' in stripped or 'Test Steps' in stripped:
                section_topic = _make_topic('📋 测试步骤')
                _add_child(current_tc_topic, section_topic)
                current_section_topic = section_topic
                current_section = 'steps'

            elif '预期结果' in stripped or 'Expected Result' in stripped:
                section_topic = _make_topic('🎯 预期结果')
                _add_child(current_tc_topic, section_topic)
                current_section_topic = section_topic
                current_section = 'result'

            elif '实现参考' in stripped or 'Implementation Reference' in stripped:
                impl = re.sub(r'\*\*实现参考\*\*[：:]\s*', '', stripped)
                impl = re.sub(r'\*\*Implementation Reference\*\*[：:]\s*', '', impl)
                impl = impl.replace('**', '').strip()
                section_topic = _make_topic('💻 实现参考')
                _add_child(current_tc_topic, section_topic)
                if impl:
                    impl_topic = _make_topic(impl)
                    _add_child(section_topic, impl_topic)
                current_section_topic = section_topic
                current_section = 'impl'

            elif stripped.startswith('- ') or re.match(r'^\d+\.\s', stripped):
                if current_section_topic is not None:
                    item_text = stripped.lstrip('- ')
                    number_match = re.match(r'^(\d+)\.\s', stripped)
                    if number_match:
                        item_text = re.sub(r'^\d+\.\s', '', stripped)
                    item_text = item_text.strip().strip('-').strip()

                    if item_text:
                        item_topic = _make_topic(item_text)
                        _add_child(current_section_topic, item_topic)

    # Clean up empty children lists (topics with no children shouldn't have empty children)
    def _clean_empty(topic):
        if 'children' in topic and 'attached' in topic['children']:
            if not topic['children']['attached']:
                del topic['children']
            else:
                for child in topic['children']['attached']:
                    _clean_empty(child)

    _clean_empty(root_topic)

    sheet = {
        'id': _gen_id(),
        'class': 'sheet',
        'title': title,
        'rootTopic': root_topic,
    }

    return [sheet]


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("XMind Zen Format Generator v1.0")
        print("=" * 60)
        print("\nUsage:")
        print("  python generate_xmind_zen.py <markdown_file> [output_file]")
        print("\nExamples:")
        print("  python generate_xmind_zen.py test-cases.md")
        print("  python generate_xmind_zen.py test-cases.md output.xmind")
        print("\nGenerates XMind Zen (JSON-based) format compatible with:")
        print("  ✅ XMind 2020+")
        print("  ✅ XMind Zen")
        print("  ✅ XMind for iOS/Android")
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
        output_path = DEFAULT_OUTPUT_DIR / md_path.with_suffix('.zen.xmind').name
    else:
        output_path = Path(output_file)

    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    print(f"📖 Reading: {md_path}")

    modules, total, p_counts = count_test_cases(md_content)

    print("\n" + "=" * 60)
    print("XMind Zen Test Cases Summary")
    print("=" * 60)
    print(f"📦 Modules: {modules}")
    print(f"📝 Total Test Cases: {total}")
    print(f"\nPriority Distribution:")
    print(f"  🔴 P0 (Critical): {p_counts['P0']}")
    print(f"  🟠 P1 (Important): {p_counts['P1']}")
    print(f"  🔵 P2 (Normal): {p_counts['P2']}")
    print("=" * 60)

    content = build_zen_from_md(md_content)

    metadata = {
        'creator': {
            'name': 'XMind',
            'version': '3.7.0',
        },
    }

    manifest = {
        'file-entries': {
            'content.json': {},
            'metadata.json': {},
        },
    }

    with ZipFile(str(output_path), 'w', ZIP_DEFLATED) as zf:
        zf.writestr('content.json', json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, indent=2))
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    import os
    print(f"\n✅ Successfully created XMind Zen file: {output_path}")
    print(f"   File size: {os.path.getsize(output_path)} bytes")
    print("\n💡 Tips:")
    print("   - Uses XMind Zen (JSON) format for XMind 2020+ compatibility")
    print("   - All hierarchy levels preserved as attached children")
    print("   - Priority markers displayed as icons in XMind")
    print("   - Open with XMind 2020+, XMind Zen, or XMind mobile apps")


if __name__ == '__main__':
    main()