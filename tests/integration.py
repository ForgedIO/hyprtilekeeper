"""Run against an explicitly supplied disposable nested Hyprland instance."""
import json
import subprocess
import sys
import time

instance = sys.argv[1]

def ctl(*args):
    return subprocess.check_output(['hyprctl', '-i', instance, *args], text=True)

def clients():
    time.sleep(0.3)
    return json.loads(ctl('-j', 'clients'))

def dispatch(name, arg=''):
    if name.startswith('tilekeeper:'):
        result = ctl('eval', 'assert(hl.plugin.tilekeeper.' + name.split(':')[1] + '())')
        assert result.strip() == 'ok', result
    else:
        result = ctl('dispatch', 'hl.dsp.focus({window = ' + json.dumps(arg) + '})')
        assert result.strip() == 'ok', result

def geometry():
    return {c['address']: (c['at'], c['size']) for c in clients()}

initial = clients()
assert len(initial) == 3 and all(c['initialTitle'].startswith('keeper-') for c in initial), 'Requires three disposable keeper terminals'
baseline = geometry()
for c in initial:
    dispatch('focuswindow', 'address:' + c['address'])
    dispatch('tilekeeper:minimize')
    assert next(w for w in clients() if w['address'] == c['address'])['hidden']
    dispatch('tilekeeper:restore')
    assert geometry() == baseline, (baseline, geometry())
    assert not any(w['hidden'] for w in clients())
print('PASS: every tile restores exact coordinates and dimensions')
for c in initial:
    dispatch('focuswindow', 'address:' + c['address'])
    dispatch('tilekeeper:minimize')
assert all(c['hidden'] for c in clients())
for c in reversed(initial):
    dispatch('tilekeeper:restore')
    assert not next(w for w in clients() if w['address'] == c['address'])['hidden']
assert geometry() == baseline
print('PASS: all tiles hidden and restored in reverse order')
ctl('dispatch', 'hl.dsp.window.resize({x=73,y=0,relative=true})')
baseline = geometry()
dispatch('tilekeeper:minimize')
dispatch('tilekeeper:restore')
assert geometry() == baseline
print('PASS: unequal split restores exactly')
victim = clients()[0]
dispatch('focuswindow', 'address:' + victim['address'])
dispatch('tilekeeper:minimize')
ctl('dispatch', 'hl.dsp.window.close({window=' + json.dumps('address:' + victim['address']) + '})')
time.sleep(0.5)
assert len(clients()) == 2
ctl('eval', 'hl.plugin.tilekeeper.restore()')
assert not any(c['hidden'] for c in clients())
print('PASS: closing a hidden window leaves remaining tiles usable')
