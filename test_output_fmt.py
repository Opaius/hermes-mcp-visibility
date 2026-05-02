#!/usr/bin/env python3
"""Tests for output_fmt.py"""
import json
import sys
sys.path.insert(0, '/root/hermes-mcp-visibility-v2')
from output_fmt import format_result, optimize, format_header

errors = []

# TEST 1: Empty JSON array
fm, meta = format_result('[]')
print(f'TEST 1 empty-array: fmt={meta["fmt"]} saved={meta["savings_pct"]}%')
if meta['fmt'] != 'passthrough': errors.append('TEST 1')

# TEST 2: Empty JSON object  
fm, meta = format_result('{}')
print(f'TEST 2 empty-obj: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 2')

# TEST 3: List of dicts <= 8 keys => md-table
data = json.dumps([{'name':'Alice','age':30,'city':'NYC'},{'name':'Bob','age':25,'city':'LA'}])
fm, meta = format_result(data)
lines = fm.splitlines()
print(f'TEST 3 md-table: fmt={meta["fmt"]} saved={meta["savings_pct"]}% lines={len(lines)}')
if meta['fmt'] != 'md-table': errors.append('TEST 3')
if len(lines) != 5: errors.append(f'TEST 3b (expected 5 lines, got {len(lines)})')
if '| name | age | city |' not in fm: errors.append('TEST 3c')

# TEST 4: Dict => YAML (must be >200 chars to trigger YAML)
data = json.dumps({
    'server': 'production-api',
    'status': 'operational',
    'version': '2.4.1',
    'uptime': '142d 7h 33m',
    'endpoints': [
        {'path': '/api/v2/users', 'method': 'GET', 'auth': True},
        {'path': '/api/v2/users', 'method': 'POST', 'auth': True},
        {'path': '/api/v2/health', 'method': 'GET', 'auth': False},
    ]
})
print(f'TEST 4 json-size: {len(data)} chars')
fm, meta = format_result(data)
print(f'TEST 4 yaml: fmt={meta["fmt"]} saved={meta["savings_pct"]}%')
if meta['fmt'] != 'yaml': errors.append('TEST 4')

# TEST 5: Small dict => passthrough
data = json.dumps({'ok':True,'count':42})
fm, meta = format_result(data)
print(f'TEST 5 small-dict: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 5')

# TEST 6: HTML => markdown
html = '<html><body><h1>Hello</h1><p>World</p></body></html>'
fm, meta = format_result(html)
print(f'TEST 6 html: fmt={meta["fmt"]} result={repr(fm)}')
if meta['fmt'] != 'markdown': errors.append('TEST 6')

# TEST 7: Large text > 100 lines => truncated
big = 'line\n' * 150
fm, meta = format_result(big)
print(f'TEST 7 truncate: fmt={meta["fmt"]} o={meta["original_bytes"]} f={meta["formatted_bytes"]}')
if meta['fmt'] != 'truncated': errors.append('TEST 7')
if 'omitted=50' not in fm: errors.append('TEST 7b')

# TEST 8: Plain text passthrough
fm, meta = format_result('hello world')
print(f'TEST 8 plain: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 8')

# TEST 9: List of dicts with >8 keys => passthrough
keys = {f'key{i}': i for i in range(10)}
data = json.dumps([keys])
fm, meta = format_result(data)
print(f'TEST 9 many-keys: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 9')

# TEST 10: optimize() wrapper — needs enough data to beat passthrough guard
data = json.dumps([
    {'name':'Alice','age':30,'city':'NYC'},
    {'name':'Bob','age':25,'city':'LA'},
    {'name':'Charlie','age':35,'city':'SF'}
])
result = optimize(data)
print(f'TEST 10 optimize: starts_with_header={result.startswith("[vis fmt=md-table")}')
if not result.startswith('[vis fmt=md-table'): errors.append('TEST 10')

# TEST 11: Pipe escaping in md-table
data = json.dumps([{'name':'foo|bar','val':'baz'}])
fm, meta = format_result(data)
print(f'TEST 11 pipe-escape: fmt={meta["fmt"]}')
# The escaped pipe should be foo\|bar — a backslash then pipe
if 'foo\\|bar' not in fm: 
    print(f'  DEBUG fm={repr(fm)}')
    errors.append('TEST 11')

# TEST 12: format_header
h = format_header('md-table', rows=47, cols=5, saved_pct=62.3)
print(f'TEST 12 header: {h}')
if h != '[vis fmt=md-table rows=47 cols=5 saved=62%]': errors.append('TEST 12')

# TEST 13: List of non-dicts => passthrough
fm, meta = format_result(json.dumps([1, 2, 3]))
print(f'TEST 13 non-dict-list: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 13')

# TEST 14: Whitespace-only string
fm, meta = format_result('   \n  ')
print(f'TEST 14 whitespace: fmt={meta["fmt"]}')
if meta['fmt'] != 'passthrough': errors.append('TEST 14')

print()
if errors:
    print(f'FAILED: {errors}')
    sys.exit(1)
else:
    print('ALL 14 TESTS PASSED')
