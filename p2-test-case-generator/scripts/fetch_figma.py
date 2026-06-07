#!/usr/bin/env python3
"""
Fetch Figma file structure and interaction data via REST API.

Extracts:
- Page hierarchy and frame structure
- Text content and component names
- Prototype interaction flows (click → navigate, click → overlay, etc.)
- Form fields, buttons, and interactive elements

Usage:
    python fetch_figma.py <figma_url> [--token TOKEN] [--output OUTPUT] [--images]

Environment:
    FIGMA_ACCESS_TOKEN - Figma Personal Access Token (or pass via --token)
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path


FIGMA_API_BASE = "https://api.figma.com/v1"
FIGMA_IMAGE_BASE = "https://api.figma.com/v1/images"


def extract_file_key(url):
    patterns = [
        r'figma\.com/(?:design|file|proto)/([a-zA-Z0-9]+)',
        r'figma\.com/(?:design|file|proto)/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def extract_node_id(url):
    m = re.search(r'node-id=([0-9-]+)', url)
    if m:
        return m.group(1).replace('-', ':')
    return None


import time


def api_request(endpoint, token, timeout=60, max_retries=3):
    url = f"{FIGMA_API_BASE}{endpoint}"
    req = urllib.request.Request(url, headers={
        'X-Figma-Token': token,
    })
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"❌ Figma API 认证失败 (403)。请检查 token 是否正确。")
                sys.exit(1)
            elif e.code == 404:
                print(f"❌ Figma 文件未找到 (404)。请检查 URL 中的 file key。")
                sys.exit(1)
            elif e.code == 429:
                wait_time = 30 * (attempt + 1)
                print(f"⚠️ Figma API 请求频率超限 (429)，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})", file=sys.stderr)
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Figma API 错误 ({e.code}): {e.read().decode('utf-8', errors='replace')}")
                sys.exit(1)
        except urllib.error.URLError as e:
            print(f"❌ 网络错误: {e.reason}")
            sys.exit(1)
    print(f"❌ Figma API 请求频率超限，重试 {max_retries} 次后仍然失败。请稍后再试。")
    sys.exit(1)


def get_text_content(node):
    texts = []
    if node.get('type') == 'TEXT':
        chars = node.get('characters', '')
        if chars and chars.strip():
            texts.append(chars.strip())
    for child in node.get('children', []):
        texts.extend(get_text_content(child))
    return texts


def get_component_info(node):
    info = {
        'name': node.get('name', ''),
        'type': node.get('type', ''),
    }
    if node.get('type') == 'TEXT':
        chars = node.get('characters', '')
        if chars and chars.strip():
            info['text'] = chars.strip()
    if node.get('componentId') or node.get('componentProperties'):
        info['is_component'] = True
    return info


def extract_interactions(node, node_id_map=None):
    interactions = []
    node_id = node.get('id', '')

    if node.get('interactions'):
        for interaction in node['interactions']:
            inter = {
                'trigger': interaction.get('trigger', {}).get('type', 'UNKNOWN'),
                'action_type': interaction.get('action', {}).get('type', 'UNKNOWN'),
            }

            action = interaction.get('action', {})
            transition_node_id = action.get('destinationId') or action.get('transitionNodeID')

            if transition_node_id and node_id_map:
                target_name = node_id_map.get(transition_node_id, transition_node_id)
                inter['navigates_to'] = target_name
            elif transition_node_id:
                inter['navigates_to_id'] = transition_node_id

            if action.get('transition'):
                transition = action['transition']
                inter['transition_type'] = transition.get('type', '')
                inter['easing'] = transition.get('easing', {}).get('type', '')
                inter['duration'] = transition.get('duration', 0)

            if action.get('overlay'):
                inter['overlay'] = True

            if action.get('url'):
                inter['url'] = action['url']

            interactions.append(inter)

    for child in node.get('children', []):
        interactions.extend(extract_interactions(child, node_id_map))

    return interactions


def build_node_id_map(node, name_map=None):
    if name_map is None:
        name_map = {}
    name_map[node.get('id', '')] = node.get('name', '')
    for child in node.get('children', []):
        build_node_id_map(child, name_map)
    return name_map


def extract_ui_elements(node, elements=None):
    if elements is None:
        elements = []

    node_type = node.get('type', '')
    node_name = node.get('name', '')

    interactive_types = {
        'BUTTON', 'CHECKBOX', 'RADIO_BUTTON', 'DROPDOWN', 'TEXT_INPUT',
        'SEARCH_INPUT', 'SWITCH', 'SLIDER', 'SCROLLBAR',
    }

    likely_interactive_names = re.compile(
        r'(?i)(btn|button|click|link|tab|switch|toggle|nav|menu|modal|dialog|'
        r'popup|overlay|close|submit|delete|add|edit|save|cancel|confirm|'
        r'search|filter|dropdown|select|checkbox|radio|input|form)',
    )

    is_interactive = (
        node_type in interactive_types
        or (node.get('interactions') and len(node['interactions']) > 0)
        or (node_name and likely_interactive_names.search(node_name))
    )

    if is_interactive or node_type == 'TEXT':
        element = {
            'id': node.get('id', ''),
            'name': node_name,
            'type': node_type,
        }

        if node_type == 'TEXT':
            chars = node.get('characters', '')
            if chars and chars.strip():
                element['text'] = chars.strip()
            else:
                return elements

        if node.get('interactions'):
            element['interactions'] = []
            for interaction in node['interactions']:
                inter = {
                    'trigger': interaction.get('trigger', {}).get('type', 'ON_CLICK'),
                    'action': interaction.get('action', {}).get('type', 'NODE'),
                }
                action = interaction.get('action', {})
                dest_id = action.get('destinationId') or action.get('transitionNodeID')
                if dest_id:
                    element['interactions'][-1]['destination'] = dest_id if not element['interactions'] else dest_id
                    element['interactions'][0]['destination'] = dest_id
                if action.get('url'):
                    element['interactions'][0]['url'] = action['url']
                if action.get('overlay'):
                    element['interactions'][0]['is_overlay'] = True

        if node.get('componentProperties'):
            element['component_properties'] = node['componentProperties']

        elements.append(element)

    for child in node.get('children', []):
        extract_ui_elements(child, elements)

    return elements


def analyze_figma_file(file_data, file_key, node_id=None):
    result = {
        'file_name': file_data.get('name', 'Unknown'),
        'pages': [],
        'interaction_flows': [],
        'ui_elements_summary': [],
    }

    document = file_data.get('document', {})

    name_map = build_node_id_map(document)

    pages = document.get('children', [])

    if node_id:
        targeted_pages = []
        for page in pages:
            found = find_node_by_id(page, node_id)
            if found:
                target_page = {
                    'name': f"{page['name']} → {found.get('name', node_id)}",
                    'frames': [],
                }
                name_map = build_node_id_map(found)
                frames = found.get('children', [found])
                if found.get('type') != 'FRAME' and found.get('type') != 'COMPONENT':
                    frames = [found]
                for frame in frames:
                    frame_info = analyze_frame(frame, name_map)
                    target_page['frames'].append(frame_info)
                targeted_pages.append(target_page)
                break
        result['pages'] = targeted_pages
    else:
        for page in pages:
            page_info = {
                'name': page.get('name', 'Unnamed'),
                'frames': [],
            }
            for frame in page.get('children', []):
                frame_info = analyze_frame(frame, name_map)
                page_info['frames'].append(frame_info)
            result['pages'].append(page_info)

    all_flows = []
    all_elements = []
    for page in result['pages']:
        for frame in page.get('frames', []):
            all_flows.extend(frame.get('interactions', []))
            all_elements.extend(frame.get('ui_elements', []))

    result['interaction_flows'] = deduplicate_flows(all_flows)
    result['ui_elements_summary'] = summarize_elements(all_elements)

    return result


def find_node_by_id(node, target_id):
    if node.get('id') == target_id:
        return node
    for child in node.get('children', []):
        found = find_node_by_id(child, target_id)
        if found:
            return found
    return None


def analyze_frame(frame, name_map):
    frame_info = {
        'name': frame.get('name', 'Unnamed'),
        'type': frame.get('type', ''),
        'interactions': [],
        'ui_elements': [],
        'text_content': [],
        'child_frames': [],
    }

    interactions = extract_interactions(frame, name_map)
    frame_info['interactions'] = interactions

    elements = extract_ui_elements(frame)
    frame_info['ui_elements'] = elements

    texts = get_text_content(frame)
    frame_info['text_content'] = texts

    for child in frame.get('children', []):
        if child.get('type') in ('FRAME', 'GROUP', 'COMPONENT', 'INSTANCE', 'SECTION'):
            child_info = analyze_frame(child, name_map)
            frame_info['child_frames'].append(child_info)

    return frame_info


def deduplicate_flows(flows):
    seen = set()
    result = []
    for flow in flows:
        key = (flow.get('trigger', ''), flow.get('action_type', ''), flow.get('navigates_to', ''), flow.get('navigates_to_id', ''))
        if key not in seen:
            seen.add(key)
            result.append(flow)
    return result


def summarize_elements(elements):
    summary = {
        'buttons': [],
        'links': [],
        'form_fields': [],
        'modals_overlays': [],
        'interactive_components': [],
        'other': [],
    }

    for elem in elements:
        name = elem.get('name', '').lower()
        etype = elem.get('type', '')
        has_interactions = bool(elem.get('interactions'))

        if 'modal' in name or 'dialog' in name or 'popup' in name or 'overlay' in name:
            summary['modals_overlays'].append(elem)
        elif any(kw in name for kw in ['input', 'field', 'textarea', 'select', 'dropdown', 'search', 'checkbox']):
            summary['form_fields'].append(elem)
        elif any(kw in name for kw in ['btn', 'button', 'submit', 'save', 'cancel', 'confirm', 'delete', 'add']):
            summary['buttons'].append(elem)
        elif any(kw in name for kw in ['link', 'nav', 'tab', 'menu']):
            summary['links'].append(elem)
        elif has_interactions:
            summary['interactive_components'].append(elem)
        else:
            if etype == 'TEXT' and 'text' in elem:
                pass
            else:
                summary['other'].append(elem)

    return summary


def format_output(analysis):
    lines = []
    lines.append(f"# Figma 设计稿分析: {analysis['file_name']}")
    lines.append("")

    lines.append("## 📄 页面结构")
    lines.append("")
    for page in analysis['pages']:
        lines.append(f"### 页面: {page['name']}")
        for frame in page.get('frames', [])[:30]:
            lines.append(f"- **{frame['name']}** ({frame['type']})")
            if frame.get('text_content'):
                for t in frame['text_content'][:5]:
                    lines.append(f"  - 文本: \"{t}\"")
            for child in frame.get('child_frames', [])[:10]:
                lines.append(f"  - 子框架: **{child['name']}** ({child['type']})")
                if child.get('text_content'):
                    for t in child['text_content'][:3]:
                        lines.append(f"    - 文本: \"{t}\"")
        lines.append("")

    lines.append("## 🔗 交互流程（原型连接）")
    lines.append("")
    flows = analysis.get('interaction_flows', [])
    if flows:
        for i, flow in enumerate(flows, 1):
            trigger = flow.get('trigger', 'ON_CLICK')
            action = flow.get('action_type', 'NODE')
            target = flow.get('navigates_to', '') or flow.get('navigates_to_id', '')
            lines.append(f"{i}. 触发: **{trigger}** → 动作: **{action}** → 目标: **{target}**")
            if flow.get('is_overlay'):
                lines.append(f"   ⚠️ 这是一个弹层/覆盖层交互")
            if flow.get('url'):
                lines.append(f"   🔗 外部链接: {flow['url']}")
    else:
        lines.append("（此设计稿未设置原型交互连接）")

    lines.append("")

    lines.append("## 🖱️ 可交互元素")
    lines.append("")

    summary = analysis.get('ui_elements_summary', {})

    if summary.get('buttons'):
        lines.append("### 按钮")
        for btn in summary['buttons'][:20]:
            text = btn.get('text', '')
            name = btn.get('name', '')
            info = f"- **{name}**"
            if text:
                info += f" (文字: \"{text}\")"
            if btn.get('interactions'):
                for inter in btn['interactions']:
                    dest = inter.get('destination', '')
                    url = inter.get('url', '')
                    if dest:
                        info += f" → 跳转到: {dest}"
                    if url:
                        info += f" → 链接: {url}"
            lines.append(info)
        lines.append("")

    if summary.get('form_fields'):
        lines.append("### 表单字段")
        for field in summary['form_fields'][:20]:
            name = field.get('name', '')
            text = field.get('text', '')
            info = f"- **{name}**"
            if text:
                info += f" (占位文本: \"{text}\")"
            lines.append(info)
        lines.append("")

    if summary.get('modals_overlays'):
        lines.append("### 弹窗/覆盖层")
        for modal in summary['modals_overlays'][:10]:
            name = modal.get('name', '')
            lines.append(f"- **{name}**")
            if modal.get('interactions'):
                for inter in modal['interactions']:
                    lines.append(f"  - 交互: {inter}")
        lines.append("")

    if summary.get('links'):
        lines.append("### 导航/链接")
        for link in summary['links'][:15]:
            name = link.get('name', '')
            info = f"- **{name}**"
            if link.get('interactions'):
                for inter in link['interactions']:
                    dest = inter.get('destination', '')
                    url = inter.get('url', '')
                    if dest:
                        info += f" → {dest}"
                    if url:
                        info += f" → {url}"
            lines.append(info)
        lines.append("")

    if summary.get('interactive_components'):
        lines.append("### 其他交互组件")
        for comp in summary['interactive_components'][:15]:
            name = comp.get('name', '')
            info = f"- **{name}** ({comp.get('type', '')})"
            if comp.get('interactions'):
                for inter in comp['interactions']:
                    dest = inter.get('destination', '')
                    if dest:
                        info += f" → {dest}"
            lines.append(info)
        lines.append("")

    lines.append("## 📝 建议的交互测试用例方向")
    lines.append("")
    suggestions = generate_interaction_test_suggestions(analysis)
    for suggestion in suggestions:
        lines.append(f"- {suggestion}")

    return '\n'.join(lines)


def generate_interaction_test_suggestions(analysis):
    suggestions = []

    flows = analysis.get('interaction_flows', [])
    if flows:
        suggestions.append("✅ 页面导航流程测试 — 验证各页面间跳转是否正确")
        for flow in flows:
            trigger = flow.get('trigger', '')
            target = flow.get('navigates_to', '') or flow.get('navigates_to_id', '')
            if target:
                suggestions.append(f"✅ {trigger} 触发后跳转到 {target} 的正确性测试")

    summary = analysis.get('ui_elements_summary', {})
    if summary.get('buttons'):
        suggestions.append("✅ 按钮点击响应测试 — 验证每个按钮的预期行为")

    if summary.get('form_fields'):
        suggestions.append("✅ 表单输入验证测试 — 验证必填项、格式校验、提交逻辑")

    if summary.get('modals_overlays'):
        suggestions.append("✅ 弹窗打开/关闭测试 — 验证覆盖层的显示和关闭逻辑")

    if summary.get('links'):
        suggestions.append("✅ 导航链接测试 — 验证页面内跳转和外部链接")

    if summary.get('interactive_components'):
        suggestions.append("✅ 自定义交互组件测试 — 验证开关、下拉、选择等组件行为")

    suggestions.append("✅ 加载状态测试 — 验证页面切换时的加载状态展示")
    suggestions.append("✅ 空状态测试 — 验证无数据时的页面展示")
    suggestions.append("✅ 错误状态测试 — 验证网络错误、超时等异常情况")

    return suggestions


def main():
    parser = argparse.ArgumentParser(description='Fetch Figma file structure and interactions')
    parser.add_argument('figma_url', help='Figma file URL (e.g. https://www.figma.com/design/KEY/Name)')
    parser.add_argument('--token', help='Figma Personal Access Token (or set FIGMA_ACCESS_TOKEN env var)')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON instead of formatted text')
    parser.add_argument('--images', action='store_true', help='Also export frame images (slow, uses more API calls)')

    args = parser.parse_args()

    token = args.token or os.environ.get('FIGMA_ACCESS_TOKEN')
    if not token:
        print("❌ Error: Figma access token required.")
        print("   Set FIGMA_ACCESS_TOKEN env var or pass --token argument.")
        print("   Get your token at: https://www.figma.com/settings → Personal access tokens")
        sys.exit(1)

    file_key = extract_file_key(args.figma_url)
    if not file_key:
        print(f"❌ Error: Could not extract Figma file key from URL: {args.figma_url}")
        print("   Expected format: https://www.figma.com/design/KEY/Name or https://www.figma.com/file/KEY/Name")
        sys.exit(1)

    node_id = extract_node_id(args.figma_url)

    print(f"📖 Fetching Figma file: {file_key}" + (f" (node: {node_id})" if node_id else ""), file=sys.stderr)

    file_data = api_request(f"/files/{file_key}?depth=2", token)

    print(f"📄 File: {file_data.get('name', 'Unknown')}", file=sys.stderr)
    pages = file_data.get('document', {}).get('children', [])
    print(f"📄 Pages: {len(pages)} ({', '.join(p.get('name', '?') for p in pages)})", file=sys.stderr)

    analysis = analyze_figma_file(file_data, file_key, node_id)

    if args.json:
        output = json.dumps(analysis, ensure_ascii=False, indent=2)
    else:
        output = format_output(analysis)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n✅ Output saved to: {args.output}", file=sys.stderr)
    else:
        print(output)

    print(f"\n📊 Summary:", file=sys.stderr)
    print(f"   Pages analyzed: {len(analysis['pages'])}", file=sys.stderr)
    print(f"   Interaction flows: {len(analysis['interaction_flows'])}", file=sys.stderr)


if __name__ == '__main__':
    main()