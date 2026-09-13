#!/usr/bin/env python3
"""Build standalone skill entrypoints without rewriting upstream design documents."""

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/VoltAgent/awesome-design-md"


def quoted(value):
    # JSON strings are valid YAML scalars and preserve literal $skill references.
    return json.dumps(value, ensure_ascii=False)


def description(entry):
    return (
        f"当用户明确指定 {entry['brand']} 视觉风格，或项目已采用该风格时，"
        f"用于{entry['scope']}的设计、实现与审阅。参考特征：{entry['style']}。"
    )


def outputs(entries):
    result = {}
    for entry in entries:
        directory = entry['directory']
        name = entry['name']
        brand = entry['brand']
        folder = ROOT / 'design-md' / directory
        source_url = f"{UPSTREAM}/blob/main/design-md/{directory}/DESIGN.md"
        result[folder / 'SKILL.md'] = f'''---
name: {name}
description: {quoted(description(entry))}
metadata:
  source: {quoted(source_url)}
  provenance: "adapted"
---

# {brand} 设计参考

在用户明确选用 {brand} 风格，或项目已有此约定时，使用这份参考完成设计、实现或审阅。仅提到该品牌、使用其产品或 API，不代表选择它的视觉风格。

## 读取参考

先读取同目录的 [DESIGN.md](DESIGN.md)。它是第三方对 {brand} 网站或界面的设计分析，并非该品牌的官方规范。主要参考场景：{entry['scope']}；辨识特征：{entry['style']}。具体颜色、字体、尺寸和组件状态以原文为准。

只加载当前选定风格的文档；比较多个风格时，再读取用户要求比较的对象。文件名和产品名称不能代替对正文的阅读。

## 应用到当前任务

- 结合项目已有设计规范、组件和用户指定的改动范围，选取适用的排版、色彩角色、间距、形状、图像与交互规则。已有产品的局部修改沿用其上下文，品牌参考用于解决这次设计问题。
- 对照原文分析的页面类型判断可迁移部分。营销页面的大标题、全屏图像和宽松间距用于工作台或密集表单时，需要按任务密度重新安排；复古风格中的年代特征按用户要求保留。
- 同一页面保持选定规则的一致性。用户要求混合风格时，说明各自用于哪些部分，并处理颜色、字体与组件规则的冲突。
- 原文提到的专有字体或图片未随文档提供时，使用项目已有资源或合适替代，说明影响辨识度的替换；中文内容需检查字体回退、换行和行距。
- 新项目需要沉淀设计约定时，把实际采纳的规则写入项目自己的设计文档；已有规范做必要的局部更新。仅要求分析或审阅时，交付判断与建议即可。

实现任务通过实际页面检查排版层级、组件状态和所需屏幕尺寸；审阅任务指出可定位的问题及修改理由。交付时简要说明采用的规则和重要调整。

## 来源

设计原文：[VoltAgent/awesome-design-md]({source_url})。本目录新增技能入口和界面配置，保留原始设计文档；来源采用仓库的 MIT 许可证。
'''
        short = f"参考 {brand} 风格设计{entry['scope']}，应用配色、排版与组件规则。"
        if not 25 <= len(short) <= 64:
            raise ValueError(f"{name}: short_description must contain 25–64 characters")
        prompt = f"请使用 ${name}，先读取设计参考，再结合当前项目与页面用途完成我要求的设计工作。"
        result[folder / 'agents' / 'openai.yaml'] = (
            'interface:\n'
            f'  display_name: {quoted(name)}\n'
            f'  short_description: {quoted(short)}\n'
            f'  default_prompt: {quoted(prompt)}\n'
        )

    catalog = [
        '# 独立设计技能目录', '',
        f'共 {len(entries)} 个技能。每个技能读取同目录的 `DESIGN.md`，保留上游目录和原文。', '',
        '在支持技能的 Agent 中选择对应技能，或使用表中的调用名。品牌风格需要明确指定；安装某品牌的软件或使用其 API 不触发设计技能。', '',
        '| 品牌 / 版本 | 调用名 | 参考场景 | 视觉特征 |',
        '| --- | --- | --- | --- |',
    ]
    for entry in entries:
        catalog.append(
            f"| [{entry['brand']}](design-md/{entry['directory']}/SKILL.md) "
            f"| `${entry['name']}` | {entry['scope']} | {entry['style']} |"
        )
    catalog += [
        '', '## 维护', '',
        '`skills.json` 保存每个品牌的技能名、适用场景和简短风格介绍。`scripts/build_skills.py` 只生成技能入口、Codex 界面配置和本目录，不修改 `DESIGN.md`、原始 README 或许可证。', '',
        '修改入口规则时编辑生成脚本；修改品牌简介时编辑 `skills.json`，然后运行：', '',
        '```sh', 'python3 scripts/build_skills.py', 'python3 scripts/build_skills.py --check', '```', '',
        '同步上游设计文档后，复核对应简介；新增或删除品牌时同步调整 `skills.json`。检查命令会拒绝漏掉的品牌、失效目录、重复技能名及尚未重新生成的文件。', '',
        '每个目录的 `SKILL.md` 和 `agents/openai.yaml` 是生成文件；若要自行调整，先修改生成脚本或元数据，再重新生成。原文可独立更新，不需要改写成技能说明。', '',
        f'来源：[VoltAgent/awesome-design-md]({UPSTREAM})；原始设计文档及许可证保留。这里只增加独立技能适配，不代表任何品牌的官方授权或规范。', '',
    ]
    result[ROOT / 'SKILLS.md'] = '\n'.join(catalog)
    return result


def load_entries():
    entries = json.loads((ROOT / 'skills.json').read_text(encoding='utf-8'))
    documents = {p.parent.name for p in (ROOT / 'design-md').glob('*/DESIGN.md')}
    directories = [e['directory'] for e in entries]
    names = [e['name'] for e in entries]
    if len(set(directories)) != len(directories) or len(set(names)) != len(names):
        raise ValueError('Duplicate skill directory or name')
    if documents != set(directories):
        raise ValueError(f"Coverage mismatch: missing={sorted(documents - set(directories))}, obsolete={sorted(set(directories) - documents)}")
    for entry in entries:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', entry['name']):
            raise ValueError(f"Invalid skill name: {entry['name']}")
        if not all(isinstance(entry.get(key), str) and entry[key].strip()
                   for key in ('directory', 'name', 'brand', 'scope', 'style')):
            raise ValueError(f'Incomplete entry: {entry}')
    return sorted(entries, key=lambda e: e['directory'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify coverage and generated files without writing')
    args = parser.parse_args()
    try:
        entries = load_entries()
        expected = outputs(entries)
        unexpected = set((ROOT / 'design-md').glob('*/SKILL.md')) - set(expected)
        if unexpected:
            raise ValueError(f'Unmapped skill entrypoints: {sorted(map(str, unexpected))}')
        stale = [p for p, content in expected.items() if not p.exists() or p.read_text(encoding='utf-8') != content]
        if args.check:
            if stale:
                print('Outdated or missing generated files:', file=sys.stderr)
                for p in stale:
                    print(p.relative_to(ROOT), file=sys.stderr)
                return 1
            print(f'Validated {len(entries)} skills and {len(expected)} generated files.')
        else:
            for p in stale:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(expected[p], encoding='utf-8')
            print(f'Generated {len(entries)} skills; changed {len(stale)} files. Upstream documents untouched.')
        return 0
    except (ValueError, KeyError, OSError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
